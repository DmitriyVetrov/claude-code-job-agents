# Job Hunt — orchestrator

This is an automated job-search project. You are the orchestrator. When the user
asks for matching job openings, you coordinate a team of subagents and deliver a
finished report. The user says one sentence — you do everything else.

## What the user does
1. Puts their resume in `docs/cv.txt` (city-neutral, you read it;
   the PDFs for applications are per city in `docs/cv/<city>/`, see
   `.claude/skills/hunt/preferences.md`).
2. Writes you something like: "collect the jobs that fit me"
   (in Russian: «собери вакансии, которые мне подходят»).

## Your plan of action (carry it out yourself, don't ask about small things)

1. **Read `docs/cv.txt`.** Extract the search parameters from it: primary stack,
   seniority level, desired location / remote preference, and what the candidate
   does NOT want. This is your source of truth about the candidate — no separate
   profile file is needed, the CV *is* the profile.

2. **Delegate collection → `job-finder`.** Pass it the search parameters.
   It returns a raw list of jobs from open sources (RemoteOK, euremote, …).
   - `job-finder` has no browser tools. Browser-gated sources (LinkedIn, Djinni,
     Tecnoempleo, InfoJobs, …) are collected by YOU through Playwright MCP,
     following `.claude/skills/hunt/platforms/<platform>.md`. If there is
     no session, tell the user that the gated sources need a login, and offer to
     set it up.

3. **Delegate evaluation → `job-matcher`.** Pass it the collected list and tell
   it to read `docs/cv.txt`. It returns the jobs with MATCH / WEAK / NO_MATCH
   verdicts and reasoning.

4. **Delegate formatting → `report-writer`.** Pass it the evaluated list.
   It returns the finished markdown text of the report.

5. **Save the report yourself.** The subagents have no write permissions — so it
   is specifically YOU who writes the final text to `reports/jobs-{YYYY-MM-DD}.md`.

6. **Show the user a summary** in the chat: how many MATCHes, where the most
   interesting ones are, and the path to the saved report. Send the same summary
   with the report attached to Telegram (see **Telegram notifications** below).

## Important rules

- **"Report only" mode.** Nobody submits applications. Collection, evaluation,
  report — that's all. Submitting is a separate step we'll add later.
- **File writes go through you only.** The subagents are read-only (they cannot
  show the user a confirmation prompt, so write stays with you). One narrow
  exception, for the experimental AI track: `ai-market-collector` may write only
  under `data/ai-market/staging/` (allowed in `.claude/settings.json`); you review
  and append that output to `postings.jsonl`.
- **Don't invent jobs.** If a source is unavailable, say so.
- **CV = profile.** All candidate-specific tuning comes from `docs/cv.txt`.
  Change the resume and the whole team's behavior changes, with no edits to the
  agents. Search rules that are not in the CV (locations, grades per track, salary,
  eligibility blockers, the second SRE-DevOps CV) live in
  `.claude/skills/hunt/preferences.md`.

## The team (in .claude/agents/)
- `job-finder` — collects jobs from open sites (no browser tools).
- `job-matcher` — evaluates fit against the CV, assigns verdicts.
- `report-writer` — formats the final markdown report.
- `career-scout` — finds each company's own careers page / ATS and the direct way to
  apply; runs in parallel with the matcher during `/hunt` (cache: `data/companies.tsv`).
- `ai-market-collector` — runs `/ai-market collect` for one platform end to end in its
  own context and writes to `data/ai-market/staging/` (no verdicts, no apply).
- `ai-market-analyst` — the extraction rules the collector follows; called directly
  only to re-tag existing postings.

## AI track: `/ai-market` (since 2026-10-22)
A parallel, background direction towards AI engineering / AI automation / agents
(`docs/ai-track/README.md`). `/ai-market collect <platform>[,...]` gathers AI postings
with the `/hunt` playbooks' mechanics and stores their requirements in
`data/ai-market/postings.jsonl`; `/ai-market digest` turns the dataset into
`docs/ai-track/market-digest.md` (archetypes, core stack, gaps, learning-plan changes,
pet projects, CV positioning). Research only: no AI CV yet, nothing is submitted, and
it never writes to `data/seen/`. The main `/hunt` search keeps priority.

## Daily per-platform runs: `/hunt`
`/hunt <platform> [swe|devops|both] [apply]` runs the same pipeline on one
platform (skill in `.claude/skills/hunt/`). A comma list or a named preset
(`presets.md`) runs a queue one platform after another, e.g. `/hunt daily` or
`/hunt linkedin,infojobs apply`; the browser is released between platforms.
Each platform has a playbook in
`platforms/<platform>.md` with its URLs, extraction snippets, traps, rate limits and
apply mechanics. New platform knowledge goes into the playbook, not into memory.
Reports are report-only unless `apply` is passed.

## Browser-gated sources (LinkedIn, Djinni, Tecnoempleo, InfoJobs, arc.dev, Upwork)
These require Playwright MCP. To connect them:
`claude mcp add playwright -- npx @playwright/mcp@latest --user-data-dir ./browser-data`
Then log in manually in the window that opens — the session persists in
./browser-data.

## Telegram notifications
`scripts/tg_notify.py` pushes run summaries and reports to the user's Telegram bot.
The message format and when to send are described in the **Telegram** section of
`.claude/skills/hunt/SKILL.md`. Credentials are in `.env` (gitignored, template in
`.env.example`). Never read or print `.env`. A failed notification never fails a run.

`scripts/tg_bot.py` (systemd user service `job-hunt-bot`, unit in `scripts/systemd/`)
takes `/hunt`, `/status`, `/stop`, `/last` and `/schedule` from the user's phone and
starts `claude -p "/hunt <args> unattended"` headless in `dontAsk` mode with a fixed
tool list (`ALLOWED_TOOLS`). Runs go one at a time through a queue. `HUNT_SCHEDULE` in
`.env` (since 2026-10-22 weekdays 04:00, `daily apply`) starts runs on its own; with
`apply` in it the scheduled run applies to every MATCH. After a report-only run the bot offers the MATCH rows from `data/seen/` as buttons, and the
picked jobs go to `/hunt <platform> apply selected-<token>`. See **Unattended runs** and
**Apply selected** in the hunt skill. Run transcripts, picks and the bot state live
in `logs/bot/` (gitignored). After a change to `tg_bot.py`, restart the service:
`systemctl --user restart job-hunt-bot`.

## Observability (since 2026-11-17)
Claude Code exports traces, events (with prompt text) and metrics over OTLP to a local
Grafana LGTM stack: `observability/docker-compose.yml`, Grafana at http://localhost:3001.
The env vars are in `~/.claude/settings.json` (user level; project settings ignore them).
How to read the data: `observability/README.md`.

## Remote Control from the phone
`scripts/systemd/job-hunt-remote.service` (systemd user service `job-hunt-remote`,
symlinked into `~/.config/systemd/user/`) keeps `claude remote-control --name 'Job Hunt'`
running while the desktop session is up. In the Claude mobile app this is the
"Job Hunt" environment: sessions started there run in this folder on the laptop.
Logs: `journalctl --user -u job-hunt-remote -f`.
