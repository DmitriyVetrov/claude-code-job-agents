# <Platform name>

> Last verified: YYYY-MM-DD · Access: open HTTP | browser (logged in) | browser (guest) · Apply: yes | no
> One line: what this platform is and why it is worth a run.

Copy this file to `platforms/<platform>.md` (lower-case, no spaces; the file name is the
`/hunt` argument). Write mechanics only: no passwords, the candidate's contact
details, account IDs or names of private people. This repo is public.

## Access

How to get in: public API / RSS / HTML, or the Playwright profile `browser-data/`.
How to check that the session is logged in, and what an expired session looks like.

## Search

| Track | Query / URL |
|---|---|
| swe | ... |
| devops | ... |

URL parameters that work (and the ones that silently do nothing), the "last 24h" variant
for daily runs, pagination.

## Extraction

Where the data lives (DOM selectors, embedded JSON, API fields) and a ready snippet.
Prefer one `browser_evaluate` that returns compact JSON over `browser_snapshot`.

## Filters and traps

Noise, reposts, fake filters, geo restrictions typical for this platform.

## Rate limits

Pauses that work, what a block looks like, how long it lasts, daily caps.

## Job ID

What to store in `data/seen/<platform>.tsv` and where to read it from.

## Already applied

Where the platform shows the application history (used for dedupe).

## Apply

Step by step, including quirks of the form and how to confirm success.
Leave this section out if applying is not supported.

## Backlog

What earlier runs did not cover yet, with dates.
