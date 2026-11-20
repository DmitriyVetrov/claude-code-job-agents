---
name: ai-market
description: >-
  Market research for the AI-engineering career track: collect AI/LLM/agent job
  postings from the hunt platforms, extract structured requirements into a dataset,
  and periodically synthesise a market digest (what employers ask for, gaps against
  the candidate, what to learn, which pet projects to build, how to position the CV).
  Research only: never applies.
  Usage: /ai-market collect <platform>[,<platform>...] [window] | /ai-market digest | /ai-market status
argument-hint: collect <platform>[,...] [24h|week|month] | digest | status
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash(date *) Bash(ls *) Bash(wc *) Bash(curl *) Bash(python3 scripts/ai_market_stats.py *) Bash(python3 scripts/tg_notify.py *) mcp__playwright__browser_navigate mcp__playwright__browser_evaluate mcp__playwright__browser_snapshot mcp__playwright__browser_wait_for mcp__playwright__browser_tabs mcp__playwright__browser_close
---

# AI market research

Invocation: `/ai-market $ARGUMENTS`

- Today: !`date +%F`
- Dataset size: !`wc -l data/ai-market/postings.jsonl`

Background: the candidate (a C#/.NET engineer) is opening a parallel track towards AI
engineering / AI automation / agent development. See `docs/ai-track/README.md`. There is
no AI CV yet, so this skill **studies the market** and never submits anything. The
main `/hunt` search is unchanged and keeps its priority.

Files:

| Path | What |
|---|---|
| [search.md](search.md) | AI search phrases per platform, regions, caps |
| [taxonomy.md](taxonomy.md) | Controlled vocabulary for archetypes and skill tags. Counts only work if tags are from this list. |
| `data/ai-market/postings.jsonl` | The dataset: one JSON object per posting (schema in taxonomy.md) |
| `scripts/ai_market_stats.py` | Deterministic counts over the dataset (markdown tables) |
| `docs/ai-track/portfolio.md` | What the candidate has already built (used for the gap analysis) |
| `docs/ai-track/learning-plan.md` | The living learning plan; the digest proposes changes to it |
| `docs/ai-track/market-digest.md` | The latest digest (overwritten; older versions live in git) |

## Arguments

- `collect <platforms>`: platforms are `/hunt` playbook names or aliases (`li`, `remote`,
  `djinni`, `upwork`, ...). Only platforms listed in search.md are supported; for any
  other, say so and skip it. Optional window: `24h`, `week` (default), `month`.
- `digest`: rebuild the digest from the whole dataset.
- `status` (or no arguments): print the dataset size, the date range, postings per
  platform (`python3 scripts/ai_market_stats.py --summary`), and when the digest was
  last built. Change nothing.

## collect

The orchestrator only coordinates: each platform is collected end to end by its own
`ai-market-collector` subagent (cards, dedupe, full descriptions, extraction), which
writes `data/ai-market/staging/<platform>-<today>.jsonl` and returns a short summary.
Raw pages and descriptions never enter the orchestrator's context.

1. **Split the platforms.** HTTP-only (`linkedin` via the guest endpoint,
   `remote-boards`) and browser ones (`djinni`, `upwork`: Playwright, logged in). Only
   platforms listed in search.md are supported.
2. **Launch the collectors.** Prompt each with `platform`, `window`, `today`, and
   "browser: yes" or "browser: no, HTTP only".
   - HTTP-only collectors run **in parallel** (one message, several Agent calls).
   - Browser collectors run **one after another**: there is one browser and one
     session. The browser chain may run at the same time as the HTTP-only group.
   - Before the browser chain, check Playwright is connected; if the session is logged
     out, report it and skip that platform (never wait on a login more than once).
3. **Review each staging file** when its collector returns:
   `python3 scripts/ai_market_stats.py --validate data/ai-market/staging/<file>`. Fix or
   drop bad lines, never append them as is. Grep the file for ids already in
   `postings.jsonl` (two collectors can meet the same posting only on the same platform,
   so this is a safety check).
4. **Append** each clean staging file to `data/ai-market/postings.jsonl`, then delete the
   staging file and its `.work/` folder. Proposed tags from the summaries go to
   taxonomy.md's "Proposed tags" section for the user to accept.
5. **Run note.** Save `reports/ai-market-<today>.md` (`-2`, `-3` if taken) from the
   collector summaries: platforms, phrases, cards seen / new / skipped and why, the
   highlights, then every `hunt_candidate` (a real .NET/C# role with an AI part that
   `/hunt` can apply to now). No verdicts, no apply.
6. **Summary** in chat and in Telegram (format of `/hunt`'s **Telegram** section, header
   `🧭 /ai-market collect`): new postings per platform, dataset size, top 5 must-have
   tags of this batch, the hunt candidates with links. Attach the run note.
7. **Release the browser** if it was opened. Playbook drift reported by a collector goes
   into that playbook (as in `/hunt` step 8): the orchestrator edits it, not the collector.

Never write to `data/seen/*.tsv`: those registries drive `/hunt` dedupe and the
Telegram apply buttons. A `hunt_candidate` reaches the job search only through the
user or a `/hunt` run.

## digest

1. Run `python3 scripts/ai_market_stats.py` (all postings) and
   `python3 scripts/ai_market_stats.py --reachable` (only `eligible_from_spain` = yes or
   unclear). Under 50 postings, say the sample is small and mark every conclusion as
   preliminary; under 20, stop and suggest another collect.
2. Read `docs/cv.txt`, `docs/ai-track/portfolio.md`,
   `docs/ai-track/learning-plan.md`, and the previous `docs/ai-track/market-digest.md`
   if any (to report what changed). Grep the dataset for the `responsibilities` and
   `signals` of the top archetypes rather than reading the whole file.
3. Write `docs/ai-track/market-digest.md` yourself (main session, not a subagent), in
   English, with these sections:
   1. **Dataset**: size, date range, platforms, regions, share reachable from Spain.
   2. **Role archetypes**: share of postings, what the job actually is (2-3 lines from
      the responsibilities), typical seniority and salary, readiness for the candidate.
   3. **The core stack**: must-have tags above ~25% of postings, then the next tier.
      Languages: Python vs TypeScript vs C# share; how often .NET appears at all.
   4. **What separates candidates**: nice-to-have tags and `signals` that recur
      (production evals, cost/latency work, customer-facing delivery, ...).
   5. **What the market does not ask for**: things in the learning plan that postings
      rarely mention (for example course badges), so time is not spent there.
   6. **Gaps, ranked**: `gap` tags by frequency in reachable postings, each with "how to
      close it" (course from learning-plan.md, a portfolio change, or a pet project).
   7. **Learning plan changes**: a concrete list of additions, removals and reorderings
      for learning-plan.md, each with the numbers behind it.
   8. **Pet projects**: 2-3 ideas, each closing the top gaps and reusing portfolio.md
      projects where possible. One finished project over many started ones.
   9. **CV positioning**: headline options, the keywords that recur in titles and
      must-haves, which existing experience to lead with, and claims in the current CV
      that need visible proof (a repo, a demo) before an AI interview.
   10. **Freelance demand** (when Upwork data exists): what clients pay for, budgets.
   11. **Changes since the last digest**.
4. Apply the learning-plan changes to `docs/ai-track/learning-plan.md` only after the
   user agrees in chat. List them in the summary.
5. Summary in chat and Telegram (header `🧭 /ai-market digest`): sample size, top 3
   archetypes, top 5 gaps, the proposed plan changes. Attach the digest.

## Rules

- Do not invent postings or requirements. A tag goes into `must_have` only when the
  posting requires it ("required", "must", "you have"); "bonus", "nice", "ideally" go to
  `nice_to_have`.
- Postings, playbooks and the dataset live in a git repo: no passwords, account IDs,
  contact details of private people.
- Unattended (Telegram bot) runs are not wired for this skill yet.
