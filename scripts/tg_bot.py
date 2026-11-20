#!/usr/bin/env python3
"""Telegram bot: run /hunt on this laptop from your phone, or on a schedule.

Runs as a systemd user service (scripts/systemd/job-hunt-bot.service). It long-polls
Telegram over outbound HTTPS (no open ports, no public IP), obeys TELEGRAM_CHAT_ID
only, and runs one headless Claude Code session at a time (the rest wait in a queue):

  claude -p "/hunt <args> unattended" --permission-mode dontAsk --allowedTools ...

Commands: /hunt [args], /status, /stop, /last [N], /schedule [spec|off], /help.
HUNT_SCHEDULE in .env (e.g. "Mon-Fri 04:00 daily apply") starts runs by itself; with
"apply" in it the scheduled run applies to every MATCH without a confirmation button.
After a report-only run the bot lists the run's MATCH jobs with buttons; the jobs you
pick are applied to by a follow-up "/hunt <platform> apply selected-<token>" run.
A failed run gets a plain-language reason and a retry button; when the Claude
subscription limit is spent, queued runs wait for its reset instead of failing at once.
See "Unattended runs" and "Apply selected" in the hunt skill. Standard library only.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_notify import (  # noqa: E402
    ENV_PATH, ROOT, TelegramError, call, chunks, load_env, save_env_value,
)

REPORTS = ROOT / "reports"
LOG_DIR = ROOT / "logs" / "bot"
SEEN_DIR = ROOT / "data" / "seen"
PLAYBOOKS = ROOT / ".claude" / "skills" / "hunt" / "platforms"
BROWSER_LOCK = ROOT / "browser-data" / "SingletonLock"

POLL_TIMEOUT = 25            # seconds Telegram holds a getUpdates request open
STALE_AFTER = 10 * 60        # a /hunt older than this (laptop was asleep or off) is not run
APPLY_CONFIRM_TTL = 10 * 60  # how long the "apply" confirmation button stays valid
PICK_TTL = 24 * 3600         # how long the job-pick buttons under a report stay valid
PICK_BATCH = 30              # jobs per pick message
RETRY_TTL = 24 * 3600        # how long the "retry" button under a failed run stays valid
LIMIT_MARGIN = 60            # seconds to wait past the usage-limit reset before starting a run
LIMIT_WARN = 0.8             # warn at start when the 5-hour window is this full
MAX_RUN = 4 * 3600           # a run is stopped after this long
STOP_GRACE = 20              # seconds between SIGTERM and SIGKILL when stopping a run
KEEP_LOGS = 30               # run logs kept in logs/bot/
CATCHUP_UNTIL = dtime(20, 0)  # a scheduled run missed in the morning still starts until then

# Tools a headless /hunt run may use. Everything else is denied (dontAsk mode), since
# nobody is at the laptop to approve a prompt. The skill's own allowed-tools add to this.
# .claude/ cannot be allowed here: Claude Code keeps it write-protected in headless
# runs, so playbook notes go to logs/bot/playbook-notes.md instead.
ALLOWED_TOOLS = [
    "Read", "Glob", "Grep",
    "Edit(reports/**)", "Edit(data/seen/**)", "Edit(logs/bot/**)",
    "Agent", "WebFetch", "WebSearch",
    "Bash(date *)", "Bash(ls *)", "Bash(curl *)",
    "mcp__playwright",
]
ARGS_RE = re.compile(r"[a-z0-9][a-z0-9, -]{0,150}")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
REGISTRY_COLS = ["id", "date", "verdict", "company", "title", "report"]
# rateLimitType of the subscription limit a run hit -> how it reads in a message.
LIMIT_NAMES = {
    "five_hour": "5-часовой лимит",
    "seven_day": "недельный лимит",
    "seven_day_opus": "недельный лимит Opus",
    "seven_day_sonnet": "недельный лимит Sonnet",
}

HELP = """🤖 job-hunt бот

/hunt <платформы|пресет> [swe|devops|both] [apply] — запустить поиск
  например: /hunt daily · /hunt linkedin devops · /hunt djinni,arcdev swe
  /hunt без аргументов — список платформ и пресетов
/status — что идёт сейчас, очередь, расписание
/stop — остановить текущий прогон и очистить очередь
/last [N] — прислать последние N отчётов (по умолчанию 1)
/schedule — расписание; /schedule Mon-Fri 04:00 daily — задать; /schedule off — выключить

После прогона без apply бот присылает MATCH-вакансии с кнопками: отметьте номера и нажмите «Подать на выбранные».
Если прогон упал, бот пишет причину и предлагает «Повторить». Если кончился лимит подписки Claude, новые запуски ждут его сброса.

Ноутбук должен быть на зарядке и не спать, вы — залогинены в рабочий стол (экран можно заблокировать)."""

log = logging.getLogger("tg_bot")


@dataclass
class Run:
    args: str
    proc: subprocess.Popen
    log_path: Path
    started: float
    lock_pid_before: int | None
    inhibitor: subprocess.Popen | None
    silent: bool = False
    stopped: str | None = None  # why the run was stopped early, if it was


@dataclass
class Queued:
    args: str
    silent: bool = False
    label: str = ""


@dataclass
class Pick:
    """A pick message: MATCH jobs of one platform the user can select to apply to."""
    platform: str
    jobs: list[dict]
    offset: int  # number of the first job in the message, minus one
    expires: float
    selected: set[int] = field(default_factory=set)


@dataclass
class Schedule:
    days: set[int]
    at: dtime
    args: str
    spec: str  # normalised "<days> <HH:MM> <args>", as saved to .env

    @property
    def until(self) -> dtime:
        return CATCHUP_UNTIL if self.at < CATCHUP_UNTIL else dtime(23, 59, 59)


def words(args: str) -> list[str]:
    return [w for w in re.split(r"[ ,]+", args) if w]


def parse_schedule(spec: str) -> Schedule:
    """'Mon-Fri 04:00 daily' -> Schedule. ValueError carries a reason for the user."""
    parts = spec.split()
    if len(parts) < 3:
        raise ValueError("нужно <дни> <ЧЧ:ММ> <аргументы /hunt>, например: Mon-Fri 04:00 daily")
    days: set[int] = set()
    for item in parts[0].lower().split(","):
        first, _, last = item.partition("-")
        if first not in DAYS or (last and last not in DAYS):
            raise ValueError(f"дни «{parts[0]}»: пишите Mon-Fri, Mon,Wed,Fri или Mon-Sun")
        i, j = DAYS.index(first), DAYS.index(last or first)
        days.update(range(i, j + 1) if i <= j else [*range(i, 7), *range(0, j + 1)])
    try:
        at = datetime.strptime(parts[1], "%H:%M").time()
    except ValueError:
        raise ValueError(f"время «{parts[1]}»: нужно ЧЧ:ММ, например 04:00") from None
    args = " ".join(parts[2:]).lower()
    if not ARGS_RE.fullmatch(args):
        raise ValueError("аргументы /hunt: только латиница, цифры, пробелы, запятые и дефис")
    if any(w.startswith("selected-") for w in words(args)):
        raise ValueError("selected-… по расписанию не запускается: это разовый выбор кнопками")
    return Schedule(days, at, args, f"{parts[0]} {at:%H:%M} {args}")


def next_run(s: Schedule, last: str | None, now: datetime) -> datetime | None:
    """When the schedule fires next: now if today's run was missed and can still catch up."""
    for d in range(8):
        day = now.date() + timedelta(days=d)
        if day.weekday() not in s.days or day.isoformat() == last:
            continue
        at = datetime.combine(day, s.at)
        if at > now:
            return at
        if now.time() < s.until:
            return now
    return None


def load_state() -> dict:
    try:
        return json.loads((LOG_DIR / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "state.json").write_text(json.dumps(state), encoding="utf-8")


def minutes_since(t: float) -> int:
    return max(1, round((time.time() - t) / 60))


def browser_lock_pid() -> int | None:
    """PID of the Chrome holding browser-data/, if one is alive on this host."""
    try:
        target = os.readlink(BROWSER_LOCK)
    except OSError:
        return None
    host, _, pid = target.rpartition("-")
    if host != socket.gethostname() or not pid.isdigit():
        return None
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    return int(pid)


def kill_stray_browser(lock_pid_before: int | None) -> None:
    """Close a Chrome the run left holding browser-data/, so the next run is not blocked."""
    pid = browser_lock_pid()
    if not pid or pid == lock_pid_before:
        return
    try:
        if b"browser-data" not in Path(f"/proc/{pid}/cmdline").read_bytes():
            return
        os.kill(pid, signal.SIGTERM)
        log.info("closed stray browser pid %s", pid)
    except OSError:
        pass


def take_inhibitor() -> subprocess.Popen | None:
    """Keep the laptop from sleeping while a run is in progress."""
    exe = shutil.which("systemd-inhibit")
    if not exe:
        return None
    proc = subprocess.Popen(
        [exe, "--what=sleep:idle", "--who=job-hunt bot", "--why=/hunt run in progress",
         "--mode=block", "sleep", "infinity"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)
    if proc.poll() is not None:
        log.warning("systemd-inhibit failed (exit %s): the laptop may sleep mid-run", proc.returncode)
        return None
    return proc


def terminate_group(proc: subprocess.Popen) -> None:
    """Stop claude and everything it started (MCP servers, the browser) as one group."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(STOP_GRACE)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def read_events(log_path: Path):
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            yield json.loads(line)
        except ValueError:
            continue


def read_result(log_path: Path) -> tuple[dict, str, dict]:
    """The final result event; any error Claude Code reported before the model ran
    (a denied `!` shell line in the skill ends the run with an empty "success"); and
    the last subscription-limit status (rate_limit_info: status, rateLimitType,
    resetsAt, unifiedWindows with each window's utilization)."""
    result, local_error, limit = {}, "", {}
    for event in read_events(log_path):
        kind = event.get("type")
        if kind == "result":
            result = event
        elif kind == "rate_limit_event":
            limit = event.get("rate_limit_info") or limit
        elif kind == "user":
            content = event.get("message", {}).get("content")
            if isinstance(content, str) and "<local-command-stderr>" in content:
                local_error = re.sub(r"</?local-command-stderr>", "", content).strip()
    return result, local_error, limit


def fmt_when(ts: float) -> str:
    at = datetime.fromtimestamp(ts)
    return f"{at:%H:%M}" if at.date() == datetime.now().date() else f"{at:%a %d.%m %H:%M}"


def usage(limit: dict) -> str:
    """'5 ч 84%, неделя 45%': how full the subscription windows were at the last check."""
    windows = limit.get("unifiedWindows") or {}
    parts = [f"{name} {round(windows[key]['utilization'] * 100)}%"
             for key, name in (("five_hour", "5 ч"), ("seven_day", "неделя"))
             if isinstance(windows.get(key, {}).get("utilization"), (int, float))]
    return ", ".join(parts)


def current_window(limit: dict) -> dict:
    """The 5-hour window from a limit status, if it has not reset since (else {})."""
    five = (limit.get("unifiedWindows") or {}).get("five_hour") or {}
    ok = isinstance(five.get("resetsAt"), (int, float)) and five["resetsAt"] > time.time()
    return five if ok and isinstance(five.get("utilization"), (int, float)) else {}


def describe_failure(result: dict, local_error: str, limit: dict,
                     stderr: str) -> tuple[str, float | None]:
    """Why a run failed, in plain words, and when the subscription limit resets if
    that was the cause (None otherwise)."""
    status = result.get("api_error_status")
    if status == 429 and limit.get("status") == "rejected":
        kind = limit.get("rateLimitType", "")
        name = LIMIT_NAMES.get(kind, f"лимит {kind}".strip())
        resets = limit.get("resetsAt")
        when = f" Сброс в {fmt_when(resets)}." if resets else ""
        return f"исчерпан {name} подписки Claude.{when}", resets
    if status == 429:
        return "Claude API ответил 429 (слишком много запросов). Обычно проходит за минуты.", None
    if status in (401, 403):
        return (f"Claude Code не авторизован (HTTP {status}): на ноутбуке запустите claude "
                "и войдите через /login."), None
    if status and status >= 500:
        return f"сбой или перегрузка на стороне Claude (HTTP {status}). Обычно проходит за минуты.", None
    if status:
        return f"ошибка Claude API (HTTP {status}).", None
    if result.get("subtype") == "error_max_turns":
        return "прогон упёрся в лимит шагов.", None
    if result.get("subtype") == "error_during_execution":
        return "Claude Code упал во время выполнения.", None
    if local_error:
        return f"скилл /hunt не запустился: {local_error[:500]}", None
    if not result:
        detail = f"\n{stderr[-800:]}" if stderr else ""
        return f"Claude Code завершился, не выдав результата.{detail}", None
    if not (result.get("result") or "").strip():
        return "Claude завершился без ответа.", None
    return "Claude сообщил об ошибке.", None


def apply_progress(args: str) -> str:
    """'обработано 10 из 24, подано 5' for an apply-selected run, from its progress log."""
    token = next((w.removeprefix("selected-") for w in words(args) if w.startswith("selected-")), "")
    try:
        total = len((LOG_DIR / f"apply-{token}.tsv").read_text(encoding="utf-8").splitlines()) - 1
        log_text = (LOG_DIR / f"apply-{token}-progress.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    outcomes = re.findall(r"^\|\s*\d+\s*\|[^|]*\|[^|]*\|\s*(\w+)", log_text, re.M)
    return (f"обработано {len(outcomes)} из {total}, подано {outcomes.count('applied')} "
            f"(logs/bot/apply-{token}-progress.md)")


def read_progress(log_path: Path) -> tuple[int, str | None, str | None]:
    """Tool calls so far, the last tool used and Claude's last text message."""
    calls, last_tool, last_text = 0, None, None
    for event in read_events(log_path):
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use":
                calls += 1
                last_tool = block.get("name")
            elif block.get("type") == "text" and block.get("text", "").strip():
                last_text = block["text"].strip()
    return calls, last_tool, last_text


def tail(path: Path, limit: int = 1500) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()[-limit:]
    except OSError:
        return ""


def prune_logs() -> None:
    runs = sorted(LOG_DIR.glob("run-*.jsonl"), reverse=True)
    for old in runs[KEEP_LOGS:]:
        old.unlink(missing_ok=True)
        old.with_suffix(".err").unlink(missing_ok=True)
    for old in LOG_DIR.glob("apply-*.tsv"):
        if time.time() - old.stat().st_mtime > 7 * 24 * 3600:
            old.unlink(missing_ok=True)


def supports_apply(platform: str) -> bool:
    """The playbook header says "Apply: yes" for platforms the skill can apply on."""
    try:
        head = (PLAYBOOKS / f"{platform}.md").read_text(encoding="utf-8")[:600]
    except OSError:
        return False
    return re.search(r"Apply:\s*yes", head) is not None


def match_rows(reports: list[Path]) -> dict[str, list[dict]]:
    """MATCH rows the run wrote to the seen registry, by platform (apply platforms only)."""
    names = {p.name for p in reports}
    out: dict[str, list[dict]] = {}
    for tsv in sorted(SEEN_DIR.glob("*.tsv")):
        if not supports_apply(tsv.stem):
            continue
        lines = tsv.read_text(encoding="utf-8").splitlines()
        if not lines:
            continue
        header = lines[0].split("\t")
        for line in lines[1:]:
            row = dict(zip(header, line.split("\t")))
            if (row.get("verdict") == "MATCH" and Path(row.get("report", "")).name in names
                    and row.get("id") not in (None, "", "-")):
                out.setdefault(tsv.stem, []).append(row)
    return out


def pick_keyboard(token: str, pick: Pick) -> dict:
    nums = [{"text": ("✅" if i in pick.selected else "") + str(pick.offset + i + 1),
             "callback_data": f"pick:{token}:{i}"} for i in range(len(pick.jobs))]
    rows = [nums[k:k + 6] for k in range(0, len(nums), 6)]
    every = len(pick.selected) == len(pick.jobs)
    rows.append([{"text": f"📨 Подать на выбранные ({len(pick.selected)})", "callback_data": f"go:{token}"}])
    rows.append([{"text": "Снять все" if every else "Отметить все", "callback_data": f"all:{token}"},
                 {"text": "Не подавать", "callback_data": f"skip:{token}"}])
    return {"inline_keyboard": rows}


class Bot:
    def __init__(self, token: str, chat_id: str, claude: str, schedule: Schedule | None = None):
        self.token = token
        self.chat_id = chat_id
        self.claude = claude
        self.schedule = schedule
        self.state = load_state()
        self.run: Run | None = None
        self.queue: list[Queued] = []
        self.pending: dict[str, tuple[str, float]] = {}  # apply confirmations: token -> (args, expiry)
        self.picks: dict[str, Pick] = {}
        self.retries: dict[str, tuple[str, float]] = {}  # retry buttons: token -> (args, expiry)
        self.limit: dict = {}  # the last subscription-limit status a run reported
        self.limit_until = 0.0  # queued runs wait until then: the usage limit is spent
        self.last_run: str | None = None

    # --- Telegram ------------------------------------------------------------

    def api(self, method: str, data: dict) -> None:
        try:
            call(self.token, method, data)
        except TelegramError as e:
            log.warning("%s", e)

    def send(self, text: str, silent: bool = False, markup: dict | None = None) -> None:
        parts = chunks(text) or ["…"]
        for i, part in enumerate(parts):
            data = {
                "chat_id": self.chat_id,
                "text": part,
                "link_preview_options": {"is_disabled": True},
                "disable_notification": silent or i > 0,
            }
            if markup and i == len(parts) - 1:
                data["reply_markup"] = markup
            self.api("sendMessage", data)

    def send_doc(self, path: Path) -> None:
        try:
            call(self.token, "sendDocument",
                 {"chat_id": self.chat_id, "disable_notification": "true"},
                 files={"document": path})
        except TelegramError as e:
            log.warning("%s: %s", path.name, e)

    def answer(self, query_id: str, text: str | None = None) -> None:
        data = {"callback_query_id": query_id}
        if text:
            data["text"] = text
        self.api("answerCallbackQuery", data)

    def set_keyboard(self, msg: dict, markup: dict | None) -> None:
        if msg:
            self.api("editMessageReplyMarkup", {
                "chat_id": self.chat_id,
                "message_id": msg["message_id"],
                "reply_markup": markup or {"inline_keyboard": []},
            })

    # --- Updates -------------------------------------------------------------

    def handle(self, update: dict) -> None:
        if "callback_query" in update:
            self.on_button(update["callback_query"])
            return
        msg = update.get("message")
        if not msg:
            return
        if str(msg["chat"]["id"]) != self.chat_id:
            log.warning("ignored a message from chat %s", msg["chat"]["id"])
            return
        text = (msg.get("text") or "").strip()
        cmd, _, rest = text.partition(" ")
        cmd = cmd.split("@")[0].lower()
        if cmd == "/hunt" and time.time() - msg.get("date", 0) > STALE_AFTER:
            sent = datetime.fromtimestamp(msg["date"]).strftime("%d.%m %H:%M")
            self.send(f"⏰ «{text}» отправлена в {sent}, когда ноутбук был недоступен. "
                      "Не запускаю: отправьте ещё раз, если ещё нужно.")
            return
        handler = {
            "/hunt": self.cmd_hunt,
            "/status": self.cmd_status,
            "/stop": self.cmd_stop,
            "/last": self.cmd_last,
            "/schedule": self.cmd_schedule,
        }.get(cmd)
        if handler:
            handler(rest.strip())
        else:
            self.send(HELP)

    def on_button(self, query: dict) -> None:
        # In a private chat the user id equals the chat id.
        if str(query.get("from", {}).get("id")) != self.chat_id:
            return
        action, _, rest = (query.get("data") or "").partition(":")
        token, _, idx = rest.partition(":")
        msg = query.get("message") or {}
        if action in ("pick", "all", "go", "skip"):
            self.on_pick(query["id"], msg, action, token, idx)
            return
        self.answer(query["id"])
        self.set_keyboard(msg, None)
        if action in ("retry", "noretry"):
            retry = self.retries.pop(token, None)
            if not retry or retry[1] < time.time():
                self.send("Кнопка устарела. Отправьте /hunt … ещё раз.")
            elif action == "retry":
                self.enqueue(retry[0], label="повтор")
            else:
                self.send("Ок, не повторяю.", silent=True)
            return
        pending = self.pending.pop(token, None)
        if not pending or pending[1] < time.time():
            self.send("Подтверждение устарело. Отправьте /hunt … apply ещё раз.")
        elif action != "apply":
            self.send("Отменено, ничего не запущено.")
        else:
            self.enqueue(pending[0])

    def on_pick(self, query_id: str, msg: dict, action: str, token: str, idx: str) -> None:
        pick = self.picks.get(token)
        if not pick or pick.expires < time.time():
            self.picks.pop(token, None)
            self.answer(query_id, "Кнопки устарели")
            self.set_keyboard(msg, None)
            return
        if action in ("pick", "all"):
            if action == "all":
                every = len(pick.selected) == len(pick.jobs)
                pick.selected = set() if every else set(range(len(pick.jobs)))
            elif idx.isdigit() and int(idx) < len(pick.jobs):
                pick.selected ^= {int(idx)}
            self.answer(query_id)
            self.set_keyboard(msg, pick_keyboard(token, pick))
            return
        if action == "go" and not pick.selected:
            self.answer(query_id, "Сначала отметьте номера")
            return
        self.answer(query_id)
        self.set_keyboard(msg, None)
        del self.picks[token]
        if action == "skip":
            self.send(f"Ок, на {pick.platform} не подаю.", silent=True)
            return
        chosen = sorted(pick.selected)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        rows = ["\t".join(REGISTRY_COLS)]
        rows += ["\t".join(pick.jobs[i].get(c, "") for c in REGISTRY_COLS) for i in chosen]
        (LOG_DIR / f"apply-{token}.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        numbers = ", ".join(str(pick.offset + i + 1) for i in chosen)
        self.send(f"📨 {pick.platform}: подаю на {len(chosen)} (№ {numbers}).")
        self.enqueue(f"{pick.platform} apply selected-{token}")

    # --- Commands ------------------------------------------------------------

    def cmd_hunt(self, rest: str) -> None:
        args = " ".join(rest.lower().split())
        if args and not ARGS_RE.fullmatch(args):
            self.send("Не понял аргументы: только латиница, цифры, пробелы, запятые и дефис.\n"
                      "Например: /hunt daily или /hunt linkedin devops")
            return
        if "apply" in words(args):
            token = secrets.token_hex(4)
            self.pending[token] = (args, time.time() + APPLY_CONFIRM_TTL)
            what = ("на выбранные вами вакансии, продолжая с места остановки"
                    if any(w.startswith("selected-") for w in words(args)) else "на все MATCH")
            self.send(f"⚠ /hunt {args} будет ПОДАВАТЬ заявки от вашего имени {what}.\n"
                      "Подтвердите в течение 10 минут.",
                      markup={"inline_keyboard": [[
                          {"text": "✅ Подавать заявки", "callback_data": f"apply:{token}"},
                          {"text": "Отмена", "callback_data": f"cancel:{token}"},
                      ]]})
            return
        self.enqueue(args)

    def cmd_status(self, _: str) -> None:
        lines = []
        limit = self.limit
        if self.run:
            limit = read_result(self.run.log_path)[2] or limit
            calls, last_tool, last_text = read_progress(self.run.log_path)
            lines.append(f"⏳ /hunt {self.run.args} идёт {minutes_since(self.run.started)} мин, "
                         f"вызовов инструментов: {calls}")
            if last_tool:
                lines.append(f"Последний инструмент: {last_tool}")
            if last_text:
                lines.append(f"Последнее сообщение Claude:\n{last_text[-600:]}")
        else:
            lines.append("Сейчас ничего не идёт.")
            if self.last_run:
                lines.append(f"Последний прогон: {self.last_run}")
        if self.queue:
            lines.append("В очереди: " + "; ".join(f"/hunt {q.args}" for q in self.queue))
        if self.limited():
            lines.append(f"🔋 Лимит подписки Claude исчерпан, запуски ждут сброса в "
                         f"{fmt_when(self.limit_until)}.")
        elif five := current_window(limit):
            lines.append(f"🔋 Лимит Claude использован: {usage(limit)} "
                         f"(5-часовое окно сбросится в {fmt_when(five['resetsAt'])}).")
        lines.append(self.describe_schedule())
        self.send("\n".join(lines))

    def cmd_stop(self, _: str) -> None:
        dropped, self.queue = self.queue, []
        if dropped:
            self.send("Очередь очищена: " + "; ".join(f"/hunt {q.args}" for q in dropped), silent=True)
        if not self.run:
            if not dropped:
                self.send("Сейчас ничего не идёт.")
            return
        self.send("Останавливаю…", silent=True)
        self.stop("по команде /stop")

    def cmd_last(self, rest: str) -> None:
        n = max(1, min(int(rest), 5)) if rest.isdigit() else 1
        files = sorted(REPORTS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
        if not files:
            self.send("Отчётов пока нет.")
        for path in files:
            self.send_doc(path)

    def cmd_schedule(self, rest: str) -> None:
        if not rest:
            self.send(self.describe_schedule())
            return
        if rest.lower() == "off":
            self.schedule = None
            save_env_value(ENV_PATH, "HUNT_SCHEDULE", "off")
            self.send("🗓 Расписание выключено.")
            return
        try:
            schedule = parse_schedule(rest)
        except ValueError as e:
            self.send(f"Не понял расписание: {e}")
            return
        self.schedule = schedule
        save_env_value(ENV_PATH, "HUNT_SCHEDULE", schedule.spec)
        # A new time that has already passed today waits for the next day instead of
        # starting a run right now.
        now = datetime.now()
        if now.time() >= schedule.at:
            self.state["last_scheduled"] = now.date().isoformat()
            save_state(self.state)
        self.send("🗓 Сохранено.\n" + self.describe_schedule())

    def describe_schedule(self) -> str:
        s = self.schedule
        if not s:
            return "🗓 Расписание выключено."
        nxt = next_run(s, self.state.get("last_scheduled"), datetime.now())
        when = f"{nxt:%a %d.%m %H:%M}" if nxt else "—"
        return (f"🗓 Расписание: {s.spec} (/hunt {s.args}). Следующий запуск: {when}. "
                f"Пропущенный запуск догоняется до {s.until:%H:%M}.")

    # --- Runs ----------------------------------------------------------------

    def tick(self) -> None:
        """Called every poll cycle: finish a run, fire the schedule, start the next queued run."""
        self.check()
        s = self.schedule
        if s:
            now = datetime.now()
            nxt = next_run(s, self.state.get("last_scheduled"), now)
            if nxt and nxt <= now:
                self.state["last_scheduled"] = now.date().isoformat()
                save_state(self.state)
                late = now - datetime.combine(now.date(), s.at) > timedelta(minutes=10)
                label = f"пропущенный запуск {s.at:%H:%M}" if late else "по расписанию"
                self.enqueue(s.args, silent=True, label=label)
        if not self.run and self.queue and not self.limited():
            q = self.queue.pop(0)
            self.start(q.args, q.silent, q.label)

    def limited(self) -> bool:
        """The subscription limit is spent: a run started now would fail at once."""
        return time.time() < self.limit_until + LIMIT_MARGIN

    def enqueue(self, args: str, silent: bool = False, label: str = "") -> None:
        if self.run or self.queue or self.limited():
            self.queue.append(Queued(args, silent, label))
            if self.run:
                why = f"сейчас идёт /hunt {self.run.args}"
            elif self.limited():
                why = f"ждёт сброса лимита Claude в {fmt_when(self.limit_until)}"
            else:
                why = "очередь"
            self.send(f"🕒 В очереди №{len(self.queue)}: /hunt {args} ({why}).", silent=silent)
        else:
            self.start(args, silent, label)

    def start(self, args: str, silent: bool = False, label: str = "") -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        prune_logs()
        log_path = LOG_DIR / f"run-{datetime.now():%Y-%m-%d_%H%M%S}.jsonl"
        prompt = " ".join(filter(None, ["/hunt", args, "unattended"]))
        cmd = [self.claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--permission-mode", "dontAsk", "--allowedTools", *ALLOWED_TOOLS]
        lock_pid_before = browser_lock_pid()
        with open(log_path, "w") as out, open(log_path.with_suffix(".err"), "w") as err:
            try:
                proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out,
                                        stderr=err, start_new_session=True)
            except OSError as e:
                self.send(f"❌ Не удалось запустить Claude Code ({self.claude}): {e}")
                return
        self.run = Run(args, proc, log_path, time.time(), lock_pid_before, take_inhibitor(), silent)
        log.info("started: %s (pid %s, log %s)", prompt, proc.pid, log_path.name)
        notes = ""
        if lock_pid_before:
            notes += ("\n⚠ Браузерный профиль сейчас занят (открыт браузер на ноутбуке?): "
                      "браузерные платформы будут пропущены.")
        five = current_window(self.limit)
        if five and five["utilization"] >= LIMIT_WARN:
            notes += (f"\n⚠ Лимит Claude уже использован: {usage(self.limit)}. Прогон может "
                      f"остановиться до сброса в {fmt_when(five['resetsAt'])}.")
        label = f" ({label})" if label else ""
        self.send(f"▶ Запущено{label}: {prompt}\n/status — ход, /stop — остановить{notes}",
                  silent=silent)

    def check(self) -> None:
        run = self.run
        if not run:
            return
        if run.proc.poll() is None:
            if time.time() - run.started > MAX_RUN:
                self.stop(f"дольше {MAX_RUN // 3600} ч")
            return
        self.finish()

    def stop(self, reason: str) -> None:
        self.run.stopped = reason
        terminate_group(self.run.proc)
        self.finish()

    def finish(self) -> None:
        run, self.run = self.run, None
        try:
            os.killpg(run.proc.pid, signal.SIGTERM)  # leftovers of a run that exited by itself
        except ProcessLookupError:
            pass
        if run.inhibitor:
            run.inhibitor.terminate()
        kill_stray_browser(run.lock_pid_before)

        result, local_error, limit = read_result(run.log_path)
        self.limit = limit or self.limit
        text = (result.get("result") or "").strip()
        ok = (run.proc.returncode == 0 and result and not result.get("is_error")
              and not run.stopped and bool(text))
        reports = sorted((p for p in REPORTS.glob("*.md") if p.stat().st_mtime >= run.started),
                         key=lambda p: p.stat().st_mtime)
        minutes = minutes_since(run.started)

        markup, status = None, "ok"
        if ok:
            msg = text
        elif run.stopped:
            msg, status = f"⏹ /hunt {run.args} остановлен: {run.stopped}.", "остановлен"
            if progress := apply_progress(run.args):
                msg += f"\nУспел: {progress}."
        else:
            msg, markup, status = self.failure_message(run, result, local_error, limit, text)
        footer = [f"⏱ {minutes} мин"]
        if result.get("num_turns"):
            footer.append(f"шагов: {result['num_turns']}")
        if denials := result.get("permission_denials"):
            tools = ", ".join(sorted({d.get("tool_name", "?") for d in denials}))
            footer.append(f"⚠ отказано в доступе: {len(denials)} ({tools})")
        if reports:
            footer.append(f"📎 отчётов: {len(reports)}")
        if used := usage(limit):
            footer.append(f"🔋 лимит Claude: {used}")
        self.send(f"{msg}\n\n{' · '.join(footer)}", silent=run.silent, markup=markup)
        for path in reports:
            self.send_doc(path)
        if ok and "apply" not in words(run.args):
            self.offer_picks(reports, run.silent)

        self.last_run = f"/hunt {run.args} — {status}, {datetime.now():%d.%m %H:%M}, {minutes} мин"
        log.info("finished: %s", self.last_run)

    def failure_message(self, run: Run, result: dict, local_error: str, limit: dict,
                        text: str) -> tuple[str, dict, str]:
        """The message for a failed run, its retry buttons and a short status for /status.
        A spent usage limit also holds the queue until the limit resets."""
        reason, resets = describe_failure(result, local_error, limit,
                                          tail(run.log_path.with_suffix(".err")))
        lines = [f"❌ /hunt {run.args} не завершён: {reason}"]
        if text:
            lines.append(f"Текст ошибки (код {run.proc.returncode}): {text[:800]}")
        if progress := apply_progress(run.args):
            lines.append(f"Успел: {progress}. Повтор продолжит с места остановки.")
        elif (last := read_progress(run.log_path)[2]) and last != text:
            lines.append(f"Последний шаг: {last[-400:]}")
        if resets and resets > time.time():
            self.limit_until = resets
            if self.queue:
                lines.append("Очередь ждёт сброса лимита: "
                             + "; ".join(f"/hunt {q.args}" for q in self.queue))
            again = f"🔁 Повторить в {fmt_when(resets)}"
        else:
            again = "🔁 Повторить"
        token = secrets.token_hex(4)
        self.retries[token] = (run.args, time.time() + RETRY_TTL)
        markup = {"inline_keyboard": [[{"text": again, "callback_data": f"retry:{token}"},
                                       {"text": "Не повторять", "callback_data": f"noretry:{token}"}]]}
        status = "лимит Claude" if resets else "ошибка"
        return "\n".join(lines), markup, status

    def offer_picks(self, reports: list[Path], silent: bool) -> None:
        """One message per platform (per PICK_BATCH jobs) with a button per MATCH job."""
        for platform, rows in match_rows(reports).items():
            for offset in range(0, len(rows), PICK_BATCH):
                token = secrets.token_hex(4)
                pick = Pick(platform, rows[offset:offset + PICK_BATCH], offset, time.time() + PICK_TTL)
                self.picks[token] = pick
                lines = [f"📝 {platform}: MATCH {offset + 1}–{offset + len(pick.jobs)} из {len(rows)}. "
                         "На какие подать?"]
                lines += [f"{offset + i}. {r.get('company', '?')} — {r.get('title', '?')[:80]}"
                          for i, r in enumerate(pick.jobs, 1)]
                lines.append("\nОтметьте номера и нажмите «Подать на выбранные». Кнопки действуют 24 ч.")
                self.send("\n".join(lines), silent=silent, markup=pick_keyboard(token, pick))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
    load_env(ENV_PATH)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        log.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in %s", ENV_PATH)
        return 1
    claude = (os.environ.get("CLAUDE_BIN") or shutil.which("claude")
              or str(Path.home() / ".local" / "bin" / "claude"))

    schedule, schedule_error = None, ""
    spec = os.environ.get("HUNT_SCHEDULE", "").strip()
    if spec and spec.lower() != "off":
        try:
            schedule = parse_schedule(spec)
        except ValueError as e:
            schedule_error = f"\n⚠ HUNT_SCHEDULE в .env не разобрано ({e}), расписание выключено."
    bot = Bot(token, chat_id, claude, schedule)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    log.info("bot started, claude=%s, schedule=%s", claude, schedule.spec if schedule else "off")
    bot.send(f"🤖 Бот на связи ({socket.gethostname()}). /help — команды.\n"
             f"{bot.describe_schedule()}{schedule_error}", silent=True)
    offset, backoff = None, 5
    try:
        while True:
            bot.tick()
            data = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message", "callback_query"]}
            if offset is not None:
                data["offset"] = offset
            try:
                updates = call(token, "getUpdates", data, timeout=POLL_TIMEOUT + 15)
                backoff = 5
            except TelegramError as e:
                log.warning("%s; retrying in %ss", e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    bot.handle(update)
                except Exception:
                    log.exception("update %s failed", update.get("update_id"))
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if bot.run:
            bot.stop("бот выключен (выход из системы или перезапуск службы)")
        bot.send("🔌 Бот выключен.", silent=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
