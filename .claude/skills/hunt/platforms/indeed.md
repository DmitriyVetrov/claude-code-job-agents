# Indeed

> Last verified: 2026-09-26 (ie.indeed.com) · Access: browser (guest) · Apply: no
> Large aggregator; useful for countries other than Spain, but heavily rate-limited without a login.

## Access

- Use Playwright only. `WebFetch` on indeed.com returns 401.
- No login is used. Without one, **page 2+ of any search redirects to
  `secure.indeed.com/auth`** (page-two sign-in), so each query yields at most ~15 jobs.
  Make up for it with many narrow queries instead of pagination.
- Country sites: `ie.indeed.com` (verified), `es.indeed.com` for Spain (same engine; not
  verified here yet).

## Search

`https://<cc>.indeed.com/jobs?q=<query>&l=<location>` plus work-mode filters:
`&sc=0kf%3Aattr(CODE)%3B` with `DSQF7` = Remote, `PAXZC` = Hybrid work. Combining the
two codes in one query was not tried; run them as two passes.

| Track | Queries |
|---|---|
| swe | `.NET developer`, `C# developer`, `software engineer .NET` |
| devops | `DevOps engineer`, `site reliability engineer`, `cloud engineer` |

## Extraction

The data is **not in the DOM** (titles in the cards have empty `innerText`).

- List:
  `window.mosaic.providerData['mosaic-provider-jobcards'].metaData.mosaicProviderJobCardsModel.results`.
  Fields: `displayTitle`, `company`, `formattedLocation`, `jobkey`,
  `salarySnippet.text`, `snippet`, `taxonomyAttributes` (the label `remote` means
  Remote or Hybrid), `jobCardRequirementsModel`.
- Full description: `/viewjob?jk=<jobkey>`. It is not in the DOM and not under
  `id="jobDescriptionText"`; it is in embedded JSON. Use the regex
  `/"sanitizedJobDescription":"((?:[^"\\]|\\.)*)"/`, then decode `<` → `<` and
  `\/` → `/`.

## Filters and traps

- **Ireland:** a Spanish permanent residence does not allow work in Ireland. Some jobs
  say "only open to Stamp 4, EU or Irish citizens" outright; most Irish "Remote" means
  remote within Ireland on an Irish payroll. Without a Critical Skills permit only
  location-independent employers are reachable. Raise eligibility early in the funnel.
- Google One Tap can push the page to `secure.indeed.com/auth` by itself and kill the
  execution context in the middle of an `evaluate`. Navigate back and retry.

## Rate limits

- 5+ quick `fetch()` calls in a row get a Cloudflare 429 on `/jobs` (the home page
  still opens). Pauses of **6-7 s** between requests inside one `browser_evaluate` work
  reliably.
- 403 "Just a moment...": a JS challenge that resolves itself. Wait ~15 s and re-read
  the page; there is no need to navigate again.
- `browser_wait_for` with a long `time` silently cuts the wait (300 s requested, ~37 s
  passed). For a real cooldown use Bash `sleep` with `run_in_background`.

## Job ID

`jobkey` (the `jk=` parameter).

## Apply

Not supported. Indeed mostly redirects to the employer's ATS.
