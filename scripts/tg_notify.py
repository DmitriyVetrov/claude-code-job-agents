#!/usr/bin/env python3
"""Send a /hunt summary (and the saved reports) to Telegram.

Setup (once):
  1. In Telegram, @BotFather -> /newbot -> copy the token.
  2. Put it in .env at the repo root: TELEGRAM_BOT_TOKEN=...
  3. Open your bot in Telegram and send it /start.
  4. python3 scripts/tg_notify.py --find-chat-id --save

Usage:
  python3 scripts/tg_notify.py --text-file summary.txt --doc reports/jobs-....md [--doc ...]
  python3 scripts/tg_notify.py --text "/hunt paused: log in to InfoJobs"

Fail-soft: a missing token or a Telegram error prints a warning and exits 0, so a
notification problem never breaks a hunt run. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
API = "https://api.telegram.org/bot{token}/{method}"
# Telegram's cap is 4096 UTF-16 units per message; emoji take two, so keep a margin.
MAX_TEXT = 3900
TIMEOUT = 30


class TelegramError(Exception):
    pass


def warn(msg: str) -> None:
    print(f"telegram: {msg}", file=sys.stderr)


def load_env(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE lines; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        os.environ.setdefault(key, value.strip().strip("\"'"))


def save_env_value(path: Path, key: str, value: str) -> None:
    """Set KEY=value in .env, replacing an existing line or appending one."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def encode_multipart(fields: dict, files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    for name, path in files.items():
        ctype = mimetypes.guess_type(path.name)[0] or "text/plain"
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
        )
        parts.append(path.read_bytes())
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call(token: str, method: str, data: dict | None = None, files: dict | None = None,
         timeout: float = TIMEOUT):
    """Call a Bot API method. Errors never include the URL, so the token stays out of logs."""
    if files:
        body, ctype = encode_multipart(data or {}, files)
    else:
        body, ctype = json.dumps(data or {}).encode(), "application/json"
    req = urllib.request.Request(
        API.format(token=token, method=method), data=body, headers={"Content-Type": ctype}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            payload = json.load(e)
        except ValueError:
            raise TelegramError(f"{method}: HTTP {e.code}") from None
    except OSError as e:
        raise TelegramError(f"{method}: network error ({getattr(e, 'reason', e)})") from None
    if not payload.get("ok"):
        desc = payload.get("description", "unknown error")
        if payload.get("error_code") in (401, 404):
            desc += " - check TELEGRAM_BOT_TOKEN"
        raise TelegramError(f"{method}: {desc}")
    return payload["result"]


def chunks(text: str, limit: int = MAX_TEXT) -> list[str]:
    """Split on line boundaries so each piece fits one Telegram message."""
    out: list[str] = []
    cur = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if cur:
                out.append(cur)
                cur = ""
            out.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) > limit:
            out.append(cur)
            cur = ""
        cur += line
    if cur.strip():
        out.append(cur)
    return out


def find_chat_id(token: str, save: bool) -> int:
    try:
        updates = call(token, "getUpdates")
    except TelegramError as e:
        warn(str(e))
        return 1
    chats: dict[int, dict] = {}
    for upd in updates:
        msg = upd.get("message") or upd.get("edited_message") or {}
        if "chat" in msg:
            chats[msg["chat"]["id"]] = msg["chat"]
    if not chats:
        warn("no messages yet: open your bot in Telegram, send it /start, then run this again")
        return 1
    for chat_id, chat in chats.items():
        name = chat.get("username") or chat.get("first_name") or chat.get("title") or "?"
        print(f"{chat_id}\t{chat.get('type')}\t{name}")
    private = [cid for cid, c in chats.items() if c.get("type") == "private"]
    if save:
        if len(private) != 1:
            warn(f"expected exactly one private chat, found {len(private)}; set TELEGRAM_CHAT_ID by hand")
            return 1
        save_env_value(ENV_PATH, "TELEGRAM_CHAT_ID", str(private[0]))
        print(f"saved TELEGRAM_CHAT_ID to {ENV_PATH.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Send a /hunt summary and reports to Telegram.")
    ap.add_argument("--text", help="message text")
    ap.add_argument("--text-file", help="file with the message text ('-' reads stdin)")
    ap.add_argument("--doc", action="append", default=[], type=Path,
                    help="file to attach (repeatable)")
    ap.add_argument("--silent", action="store_true", help="deliver without a notification sound")
    ap.add_argument("--find-chat-id", action="store_true",
                    help="list chats that wrote to the bot (setup helper)")
    ap.add_argument("--save", action="store_true",
                    help="with --find-chat-id: write the private chat's id to .env")
    args = ap.parse_args()

    load_env(ENV_PATH)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        warn("TELEGRAM_BOT_TOKEN is not set (.env at the repo root); nothing sent")
        return 1 if args.find_chat_id else 0
    if args.find_chat_id:
        return find_chat_id(token, args.save)

    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        warn("TELEGRAM_CHAT_ID is not set; run with --find-chat-id --save first; nothing sent")
        return 0

    text = args.text or ""
    if args.text_file:
        text = sys.stdin.read() if args.text_file == "-" else Path(args.text_file).read_text(encoding="utf-8")
    if not text.strip() and not args.doc:
        ap.error("nothing to send: pass --text, --text-file or --doc")

    sent_msgs = sent_docs = failed = 0
    # Only the first message rings; continuations and attachments arrive silently.
    for i, part in enumerate(chunks(text)):
        try:
            call(token, "sendMessage", {
                "chat_id": chat_id,
                "text": part,
                "link_preview_options": {"is_disabled": True},
                "disable_notification": args.silent or i > 0,
            })
            sent_msgs += 1
        except TelegramError as e:
            warn(f"FAILED {e}")
            failed += 1
    for doc in args.doc:
        if not doc.is_file():
            warn(f"FAILED attachment not found: {doc}")
            failed += 1
            continue
        try:
            call(token, "sendDocument", {
                "chat_id": chat_id,
                "disable_notification": "true" if (args.silent or sent_msgs) else "false",
            }, files={"document": doc})
            sent_docs += 1
        except TelegramError as e:
            warn(f"FAILED {doc.name}: {e}")
            failed += 1

    print(f"telegram: sent {sent_msgs} message(s), {sent_docs} document(s)"
          + (f", {failed} failed" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
