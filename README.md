# claude-code-job-agents

A multi-agent job-search system built on **Claude Code**: subagents, skills, Playwright MCP,
a Telegram control bot and OpenTelemetry observability. It collects job postings from a dozen
boards, scores each one against a CV, writes a daily report and can apply to the matches,
unattended, from a schedule or a phone.

> This is a sanitized public snapshot of a system I use every day. Personal data (CVs, search
> preferences, reports, application history) is replaced with fictional examples. It is published
> to show how the system is built, not as an installable product.

## Architecture

```mermaid
flowchart LR
    U([User: "/hunt linkedin apply"<br/>or Telegram / schedule]) --> O
    subgraph Claude Code
      O[Orchestrator<br/>CLAUDE.md + hunt skill]
      F[job-finder<br/>open APIs / feeds]
      M[job-matcher<br/>MATCH / WEAK / NO_MATCH]
      S[career-scout<br/>company careers page / ATS]
      W[report-writer<br/>markdown report]
    end
    O -- open sources --> F
    O -- gated sources --> B[(Playwright MCP<br/>logged-in browser)]
    F --> O
    B --> O
    O --> M
    O --> S
    M --> O
    S --> O
    O --> W --> O
    O --> R[reports/jobs-DATE-platform.md]
    O --> D[data/seen/*.tsv<br/>dedupe registry]
    O --> T[Telegram summary]
    O -. OTLP .-> G[Grafana LGTM]
```

**Design choices**

- **The CV is the profile.** Every agent reads `docs/cv.txt`; change the CV and the whole team
  changes its behaviour, no prompt edits. Rules not in the CV (cities, grades, salary,
  eligibility blockers) live in [`preferences.md`](.claude/skills/hunt/preferences.md).
- **Least privilege.** Subagents are read-only (`tools:` in their frontmatter); only the
  orchestrator writes files, so every write can be confirmed. One narrow exception is
  allow-listed in [`.claude/settings.json`](.claude/settings.json).
- **Knowledge in playbooks, not prompts.** Each platform has a playbook in
  [`.claude/skills/hunt/platforms/`](.claude/skills/hunt/platforms/): URLs, DOM extraction
  snippets, rate limits, traps and apply mechanics. After every run the orchestrator updates the
  playbook with what it learned, so the system gets better without code changes.
- **Report-only by default.** Applying happens only with an explicit `apply` argument or a pick
  from Telegram.
- **Browser sessions without passwords.** Gated boards (LinkedIn, InfoJobs, Djinni, ...) use a
  persistent Playwright profile; the user logs in by hand once, the agent never types a password.

## Components

| Path | What it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Orchestrator instructions: the pipeline and the rules |
| [`.claude/agents/`](.claude/agents/) | Subagents: `job-finder`, `job-matcher`, `report-writer`, `career-scout`, `ai-market-collector`, `ai-market-analyst` |
| [`.claude/skills/hunt/`](.claude/skills/hunt/) | `/hunt <platform>[,...] [swe\|devops] [apply]` skill: queueing, dedupe, apply flow, unattended mode |
| [`.claude/skills/hunt/platforms/`](.claude/skills/hunt/platforms/) | One playbook per job board |
| [`.claude/skills/ai-market/`](.claude/skills/ai-market/) | `/ai-market`: collects AI-engineering postings into a dataset and turns it into a market digest (taxonomy, extraction schema) |
| [`scripts/tg_bot.py`](scripts/tg_bot.py) | Telegram bot (systemd user service): `/hunt`, `/status`, `/stop`, `/last`, `/schedule`; starts headless `claude -p` runs in `dontAsk` mode with a fixed tool allow-list, one at a time through a queue; offers MATCH jobs as buttons to apply |
| [`scripts/tg_notify.py`](scripts/tg_notify.py) | Pushes run summaries and reports to Telegram |
| [`scripts/systemd/`](scripts/systemd/) | Units for the bot and for `claude remote-control` (drive the laptop session from the Claude mobile app) |
| [`observability/`](observability/) | Grafana LGTM stack receiving Claude Code OTLP traces, events and metrics (tokens, cost, tool calls per run) |
| [`src/`](src/) | An earlier standalone version of the same pipeline on the Claude Agent SDK (Python) |
| [`reports/jobs-example-linkedin.md`](reports/jobs-example-linkedin.md) | What a report looks like (fictional data) |

## A run, end to end

1. `/hunt daily apply` (or the 04:00 weekday schedule) expands a preset into a queue of platforms.
2. For each platform: preflight the browser session → collect cards → drop ones already in
   `data/seen/` → fetch full descriptions.
3. `job-matcher` scores each posting against the CV and preferences; `career-scout` in parallel
   finds the company's own careers page so the application can go there instead of the board.
4. `report-writer` formats the report; the orchestrator saves it and records every job in
   `data/seen/`.
5. With `apply`: fill and submit forms through Playwright using the playbook's mechanics,
   attaching the CV variant that fits the job's city and track.
6. Summary to the chat and to Telegram, browser released, next platform.

## Stack

Claude Code (subagents, skills, hooks/permissions, headless `claude -p`, remote control) ·
Playwright MCP · Python (Telegram bot, stdlib only) · systemd · OpenTelemetry → Grafana
Loki / Tempo / Prometheus · Claude Agent SDK.

## License

MIT
