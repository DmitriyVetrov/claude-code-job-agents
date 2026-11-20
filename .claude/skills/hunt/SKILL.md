---
name: hunt
description: >-
  Daily job search on one platform or a queue of platforms (LinkedIn, Djinni,
  Tecnoempleo, InfoJobs, Indeed, arc.dev, Upwork, ...) against the candidate's two
  CVs: collect, evaluate, save a report, and apply only when explicitly asked.
  Usage: /hunt <platform|preset>[,<platform>...] [swe|devops|both] [apply]
argument-hint: <platform|preset>[,...] [swe|devops|both] [apply]
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash(date *) Bash(ls *) mcp__playwright__browser_navigate mcp__playwright__browser_evaluate mcp__playwright__browser_snapshot mcp__playwright__browser_wait_for mcp__playwright__browser_tabs mcp__playwright__browser_close Bash(python3 scripts/tg_notify.py *)
---

# Job research: one platform, or a queue of platforms

Invocation: `/hunt $ARGUMENTS`

- Today: !`date +%F`
- Platform playbooks (a file name without `.md` is the platform name; `template.md` is
  not a platform): !`ls "${CLAUDE_SKILL_DIR}/platforms"`

(If the playbook list above is empty, Glob `.claude/skills/hunt/platforms/*.md`. Keep
these two lines plain `date` / `ls`: an unattended run allows no other shell command,
and a denied one stops the skill before it starts.)

## 0. Parse the arguments

Split the arguments into words on spaces and commas.

- **Track**: `swe`, `devops` or `both`. Default: `both`.
- **Mode**: the word `apply` switches to apply mode. Without it the run is report-only
  (the CLAUDE.md default). Never submit anything unless the word `apply` is in this
  invocation.
- **Unattended**: the word `unattended` means the Telegram bot started this run and
  nobody is at the laptop. Follow **Unattended runs** below on top of the other steps.
- **Selected**: a word `selected-<token>` (the bot sends it with `apply` and one
  platform) means the user picked jobs in Telegram, listed in
  `logs/bot/apply-<token>.tsv`. Follow **Apply selected** below instead of steps 3-5.
- **Platforms**: every other word, lower-cased. Each one is
  - a playbook name;
  - an alias: `li` → linkedin, `te` → tecnoempleo, `ij` → infojobs, `arc` → arcdev,
    `genie` / `djini` → djinni, `parks` → industrial-parks, `companies` → company-sites,
    `remote` → remote-boards, `sk` → profesia, `gl` → globallogic;
  - or a preset from [presets.md](presets.md), which expands to its platforms in order.

  Build the queue in the order given and drop repeats (keep the first). If a word is
  unknown or the queue is empty, list the playbooks (with the one-line summary from each
  file's header) and the presets, then stop before opening anything.

Track and mode are the same for every platform in the queue: `apply` covers all of
them. A platform whose playbook has no **Apply** section stays report-only (step 6).

One platform: run steps 1-9. Two or more: follow **Queue mode** below.

## 1. Load context

1. Read [preferences.md](preferences.md). It holds the search rules that are not in
   the CV: locations, grades per track, eligibility blockers, salary, screening answers.
2. Read `platforms/<platform>.md`, the playbook. Its header line gives the access
   type (open HTTP / browser) and whether Apply is supported.
3. Read the CV(s) for the track: `docs/cv.txt` (swe),
   `docs/cv-devops.txt` (devops = Junior SRE only), or both. The PDF to
   attach depends on the job's city: see "CVs: one per city" in preferences.md.
   Offer-maximizing mode is on by default: run the playbook's `offer-max` searches too.
4. Read the seen registry: `data/seen/<platform>.tsv` for this platform, plus the other
   `data/seen/*.tsv` files for the cross-platform check in step 3 (Grep them by company
   rather than reading them whole). See **Seen registry** at the end for the format.

## 2. Preflight (browser platforms only)

- Playwright MCP tools (`mcp__playwright__*`) must be available. If they are not and the
  playbook names a non-browser fallback (LinkedIn's guest endpoint), use it and say in
  the report what was lost (for example "guest mode: no personal recommendations").
  Otherwise say that the platform needs the browser (setup command in CLAUDE.md) and
  stop. Never fill the gap with guessed or invented listings.
- If the browser does not start because the profile is in use ("Browser is already in
  use", or the `browser-data/SingletonLock` points to a live Chrome), another session is
  holding `browser-data/`. Say so and stop. Do not delete the lock and do not switch to
  a different profile.
- Check that the session is logged in (the playbook's **Access** section says how)
  unless the playbook says this mode works without a login (InfoJobs searches as a
  guest; it needs the login only for apply). If it is not logged in, open the login
  page in the visible browser, ask the user to log in themselves, send a Telegram
  ping (see **Telegram**: the user may be away from the screen), and wait. Never type
  or store passwords.

## 3. Collect

- Run the searches from the playbook's **Search** section for the chosen track(s).
  On a daily run prefer the playbook's "last 24h" variant when it has one.
- Browser platforms: collect here, in the main session. `job-finder` has no Playwright
  tools. Open-HTTP platforms: you may delegate to `job-finder`; tell it to Read the
  playbook first and return the raw list.
- Keep the raw list as JSON in the scratchpad: id, title, company, location, url,
  salary, posted, description (up to ~1200 chars), track guess.
- Dedupe within the run (company + title), then against the seen registry:
  - same platform, same ID → skip;
  - registry rows with id `-` (backfilled from old reports that had no links) → match
    by normalised company + title; skip if that row is less than 60 days old, otherwise
    keep the job and note "seen on <date>" (roles get re-opened);
  - same company + title in another platform's file → if that row is `applied`, skip
    ("already applied via <platform>"); otherwise keep the job and note
    "also reported on <platform>, see <report>";
  - rows with verdict `backlog` are never skipped: they are unfinished work from an
    earlier run, so put them first.
- Also dedupe against the platform's own "already applied" view if the playbook names one.
- Drop hard blockers from preferences.md right away (geo / citizenship / language
  restrictions, Senior+ titles in the DevOps track, excluded companies). Keep a
  one-line reason for each drop; it goes into the report's "Filtered out" section.
- Follow the playbook's rate limits. Stop cleanly when a daily cap is hit and say so.

## 3b. Company sites with `career-scout` (in parallel with step 4)

Right after collection and the hard-blocker filter, start `career-scout` in the
background (run_in_background) at the same time as `job-matcher`. It needs no browser,
so it never competes with the Playwright session.

- Input: the distinct companies of the remaining jobs (name, LinkedIn company URL if
  known, job title, city, job ID). Before passing them, Grep `data/companies.tsv`: a
  company checked less than 14 days ago goes in with its cached row (the scout only
  re-checks the role); one checked earlier is searched again. Split more than ~40
  companies into several scouts.
- Output: one TSV row per company (see the agent). Write/refresh the company rows in
  `data/companies.tsv` yourself (columns `company, website, careers_url, ats,
  apply_method, hq_city, agency, checked, note`; one row per company, update in place).
- Use the result in step 6. New ATS mechanics learned while applying go into
  `platforms/company-sites.md`.

## 4. Evaluate with `job-matcher`

Pass the remaining list and tell it to Read the CV(s) above and
`.claude/skills/hunt/preferences.md`. State which track each job is scored
against. DevOps/SRE-track jobs are a legitimate track here: the matcher's
"recent-experience trap" does not apply to them, but the reason line must say
"DevOps/SRE track".

## 5. Report with `report-writer`, then save

- Pass the evaluated list plus the "Filtered out" reasons.
- Save the returned markdown to `reports/jobs-<today>-<platform>.md`. If that file
  already exists, add `-2`, `-3`, and so on.
- Append every reported job (MATCH, WEAK, NO_MATCH and filtered) to
  `data/seen/<platform>.tsv`, with `report` = the path you just saved. If the job's
  ID is already there (a `backlog` row, or a re-check), update that row instead of
  adding a second one.

## 6. Apply (only with `apply`)

- Apply only if the playbook has an **Apply** section. Otherwise say that apply is not
  supported on this platform yet and stay report-only.
- **Company site first** (user rule, 2026-10-22). For each job to apply to, look at the
  scout's row: `role-form` → apply on the company site/ATS instead of the platform;
  only companies without their own portal go through Easy Apply / the platform. Never
  apply to the same role on both. A `general-form` company with no matching role gets
  one open application (see "Open applications" in preferences.md). `email` → list it
  under "Needs manual review" with the address (no emails are sent automatically).
- Apply to MATCH jobs, and to WEAK ones only if the user asked. Pick the CV per job by
  its track.
- Salary fields, screening answers and follow/consent checkboxes: see preferences.md.
- Never fabricate an answer. If an honest answer to a mandatory question would
  disqualify the candidate, or the option wording is ambiguous, skip the job and list
  it under "Needs manual review".
- Confirm each submission the way the playbook describes. Add an "Applied" section to
  the report and set those rows to `applied` in the seen registry. Jobs you shortlisted
  but did not reach (cap, time) go in as `backlog`.

## 7. Summarise in chat

Give: new jobs found / filtered out / MATCH / WEAK; the top 3-5 MATCH jobs with one
line each; applications sent (if any); anything that blocked the run (login, cap,
HTTP 429); and the report path. Then send the same summary to Telegram (see
**Telegram**).

## 8. Keep the playbook current

If the platform behaved differently from its playbook (new selector, changed URL
parameter, new trap, cap hit), fix `platforms/<platform>.md` in this run and bump its
"Last verified" date. In an attended run, also apply the notes that unattended runs
left in `logs/bot/playbook-notes.md` for this platform, then remove those sections
(delete the file when it is empty). Platform knowledge lives in the playbooks, not in memory. For a
new platform, copy `platforms/template.md`.

Playbooks are committed to a public repo: write mechanics only. Never put passwords,
the candidate's contact details, account IDs or names of private people in them
(a company's public HR address is fine).

## 9. Release the browser

If this run opened the browser, call `browser_close` once the platform is finished,
and also when the run stops early for any reason (login, cap, error). Chrome locks
`browser-data/` while the browser is open, so an idle session blocks every other
session that needs the profile. Logins survive the close: cookies stay in the profile.

## Queue mode

Two or more platforms run one after another in this session, never in parallel: they
share the `browser-data/` profile.

1. **Load once.** Read preferences.md and the CV(s) (steps 1.1 and 1.3) once for the
   whole queue. Read each playbook and its registry (steps 1.2 and 1.4) when its turn
   comes.
2. **Login preflight for the whole queue.** Before collecting anything, check the
   session of every browser platform in the queue that needs a login in this mode
   (step 2). Ask the user once to log in to all logged-out platforms in the visible
   browser, send one Telegram ping that names them all, and wait. If the user cannot log in now, use the playbook's non-browser
   fallback if it has one; otherwise mark the platform `skipped: login` and drop it from
   the queue. After the preflight the queue runs unattended; release the browser
   (step 9) before starting the first platform.
3. **Per platform, in queue order:** steps 1.2, 1.4, 2 (a quick check that the session
   is still logged in), 3, 4, 5, 6, 8, 9. Do not start the next platform until:
   - the report is saved and its registry rows (including `applied`) are written. The
     next platform's cross-platform dedupe depends on them: a job applied to on
     LinkedIn earlier in this queue must be skipped on InfoJobs;
   - the browser is released (step 9);
   - the platform's status row is in the queue log.
4. **One platform failing does not stop the queue.** Login lost mid-run, a daily cap,
   HTTP 429, the site down, a broken selector: save what was evaluated (a partial
   report that says where it stopped; shortlisted jobs that were not reached go to the
   registry as `backlog`), release the browser, write the status row and go to the
   next platform. Stop the whole queue only when the user says so.
5. **Queue log.** Keep `hunt-queue-<today>.md` in the scratchpad: the
   invocation, the resolved queue, and one status row per finished platform (the
   columns of the summary table below). After a context compaction, the platforms that
   have a row are done; continue with the next one. Keep only the status row in
   context and do not re-quote a saved report.
6. **Summary** (replaces step 7): one table for the whole queue with the columns
   Platform, New, Filtered, MATCH, WEAK, Applied, Issues, Report. Then give the top 3-5
   MATCH jobs across all platforms, one line each, and everything that needs the user:
   skipped logins, "Needs manual review" jobs, caps and when they reset. Send it to
   Telegram as one message for the whole queue, with every report attached.

## Telegram

`scripts/tg_notify.py` sends the run's result to the user's phone through their
Telegram bot. The token and chat id live in `.env` at the repo root: never read, print
or quote that file. If the script prints "not set" or "FAILED", mention it in one line
of the chat summary and carry on. A notification problem never fails the run.

- **When.** Once at the end of the run (step 7, or queue step 6), with the saved
  reports attached. Also a short text-only ping whenever the run stops to wait for the
  user (login preflight) or ends early.
- **How.** Write the message as plain text to `tg-<today>.txt` in the scratchpad, then
  run from the repo root:
  ```
  python3 scripts/tg_notify.py --text-file <scratchpad>/tg-<today>.txt --doc reports/<report>.md [--doc ...]
  ```
  A ping: `python3 scripts/tg_notify.py --text "⏸ /hunt daily: log in to LinkedIn, InfoJobs in the browser window"`.
- **Format.** Plain text, no Markdown (Telegram shows `**`, `|` and `#` literally).
  Keep it short, since the attached report carries the details. One line per
  platform, then the top 3-5 MATCH jobs with direct links, then only the warnings
  that apply:
  ```
  🎯 /hunt daily both · 2026-10-05 · report-only
  LinkedIn: 12 new · 4 MATCH · 3 WEAK · 9 filtered
  InfoJobs: 8 new · 2 MATCH · 1 WEAK · 3 filtered

  Top MATCH:
  • Capitole — .NET Developer (Valencia, hybrid)
    https://www.linkedin.com/jobs/view/4430451516/
  • ...

  ⚠ InfoJobs: daily cap hit, resets at midnight
  ⚠ 2 jobs need manual review
  ```
  In apply mode add `· N applied` to each platform line. No contact details,
  passwords or account IDs in the message.

## Unattended runs

`scripts/tg_bot.py` starts `/hunt <args> unattended` headless (`claude -p`) when the
user sends `/hunt` to the Telegram bot. Nobody can answer a question or approve a
prompt, and the run ends as soon as you stop. So:

- **Never wait for the user.** A logged-out platform is `skipped: login`: use the
  playbook's non-browser fallback if it has one, otherwise drop it. Never open a login
  page and wait. A busy browser profile is `skipped: browser busy`. Either way, go on
  with the rest of the queue. Don't inspect `browser-data/SingletonLock` or `/proc`
  yourself: the bot checks the lock before it starts the run and tells the user.
  Just open the browser; "Browser is already in use" means busy.
- **Don't call `tg_notify.py`.** The bot sends your final answer to Telegram and
  attaches every report saved during the run. So your final answer is the Telegram
  message itself, in the **Telegram** format, and nothing else. Put every skipped
  platform in it as a ⚠ line, for example `⚠ InfoJobs: skipped, log in at the laptop`.
- **Scratch files** (the raw list, the queue log) go in `logs/bot/` rather than the
  scratchpad.
- **Playbook updates (step 8).** `.claude/` is write-protected in headless runs, so
  don't try to Edit a playbook. Append the change you would have made to
  `logs/bot/playbook-notes.md` under a `## <platform> · <today>` heading, and add one
  ⚠ line to the final answer saying so.
- **Denied tools.** Only a fixed tool list is allowed, see `ALLOWED_TOOLS` in
  `scripts/tg_bot.py`. If a tool is denied, do without it. If the platform cannot run
  without it, note that in a ⚠ line and move on.
- **`apply`** reaches an unattended run only after the user confirmed it with a button
  in Telegram, picked the jobs (see **Apply selected**), or put `apply` in the schedule
  (since 2026-10-22 the weekday run is `daily apply`). The apply rules in step 6 are
  unchanged.
- **After a report-only run** the bot reads the MATCH rows this run wrote to
  `data/seen/<platform>.tsv` and offers them to the user as buttons. So every MATCH
  needs its registry row with the real job ID (step 5). A row with ID `-` cannot be
  offered.

## Apply selected

`/hunt <platform> apply selected-<token> unattended`: after a report-only run the user
ticked some MATCH jobs under the report in Telegram. The bot wrote them to
`logs/bot/apply-<token>.tsv`, with the registry columns (`id`, `date`, `verdict`,
`company`, `title`, `report`).

A run can be cut off at any moment (the Claude usage limit, a crash, `/stop`), and the
bot then offers the user a retry with the same arguments. So the run keeps its state in
files as it goes, and a retry continues where the last run stopped.

1. Steps 1-2 as usual (preferences, playbook, CVs, registry, login check). Skip
   collection and evaluation (steps 3-4). If the file is missing or empty, say so and
   stop.
2. **Progress log** `logs/bot/apply-<token>-progress.md`. If it exists, an earlier run
   on these picks stopped midway: the jobs listed in it are done, so continue with the
   first job that is not, and use the report path from its `Report:` line. If it does
   not exist, pick the report path (`reports/jobs-<today>-<platform>-apply.md`, with
   `-2`, `-3` if taken) and create the log:
   ```
   # /hunt <platform> apply selected-<token> · <today>
   Report: reports/jobs-<today>-<platform>-apply.md

   | # | id | company | outcome | note |
   |---|---|---|---|---|
   ```
3. For each remaining job, in order: open it by its ID (the playbook's **Job ID**
   section gives the URL) and read the full description. Skip it with a one-line reason
   if:
   - the job is closed;
   - any `data/seen/*.tsv` already has it as `applied`;
   - the description shows a hard blocker from preferences.md. The earlier verdict may
     have been made from the title only.
4. Apply to the rest per step 6, with the CV for the track given in the job's row of
   its `report`. Respect the playbook's caps.
5. **Right after each job**, before opening the next one, append its row to the
   progress log: `#` = its line number in `apply-<token>.tsv`, `outcome` = `applied`,
   `skip` or `review`, `note` = the reason, or what the form asked and what you
   answered. If it was submitted, set its registry row to `applied` now, with
   `report` = the path from the `Report:` line. Never batch these to the end of the run.
6. When the list is done (or a cap stops it): write the report yourself (no
   report-writer needed) to the `Report:` path, built from the whole progress log
   (earlier runs included), with the sections Applied, Skipped (with reason), Needs
   manual review, and Not reached. Set the `review` and `skip` rows' `report` to it
   (their verdict stays `MATCH`), and the jobs not reached to `backlog`.
7. The final answer is the Telegram message:
   `📨 <platform> · applied N of M` + one line per job (✅ applied / ⏭ skipped: reason /
   ⚠ needs review) + blockers. Count across the whole progress log, and add
   `(resumed)` when an earlier run had started it.

## Seen registry

`data/seen/<platform>.tsv` holds one row per job ever analysed on that platform. It has a
header line and six tab-separated columns:

```
id	date	verdict	company	title	report
4430451516	2026-06-19	applied	Capitole	Desarrollador .NET (Sr, construction)	reports/jobs-2026-06-19-b.md
```

- `id`: the platform's job ID (see the playbook's "Job ID" section), or `-` when the
  source report had no link.
- `date`: the date of the report that analysed the job last.
- `verdict`: `MATCH`, `WEAK`, `NO_MATCH`, `filtered` (dropped by a hard blocker),
  `applied`, `backlog` (shortlisted, not done yet) or `seen` (listed without a verdict).
- `report`: the report with the reasoning. Open it when the user asks why.

Files without a playbook also exist: `wearedevelopers`, `jooble`, and `other`
(early mixed-source reports from June and July 2026). They still count for the
cross-platform check. All files were backfilled from `reports/` on 2026-10-04.
`profesia.tsv` was one of these until the playbook was added on 2026-10-05, so its
oldest rows (2026-06-19) predate the playbook's ID convention — they already use
`O<offer-id>`, which is what the playbook now specifies.

## Unavailable sources

- **talent.io**: dead (certificate error since 2026-06; merged into Welcome to the
  Jungle, whose search does not expose job cards). Skip.
- **Honeypot.io**: dead (DNS resolves, nothing listens on 80/443; checked 2026-09-10). Skip.
- **Wellfound**: no logged-in session and no playbook yet. Needs a manual login first.
