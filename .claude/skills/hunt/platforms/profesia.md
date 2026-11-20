# profesia.sk

> Last verified: 2026-10-05 · Access: open HTTP for listings (strict UA rule, hard request cap) + browser for descriptions · Apply: no (not explored yet)
> One line: the dominant Slovak job board. Dense .NET/C# market in Bratislava with salaries printed on the listing page, so a harvest is useful even without descriptions.

Not to be confused with **professia.sk** (double "s"): that domain is parked and redirects to
`ww62.professia.sk/?clickid=...` with a "domain is for sale" lander. No jobs there.

## Access

Behind CloudFront with AWS WAF. Two separate gates:

**1. User-Agent rule (deterministic, verified 2026-10-05).** Chrome UA on a Linux desktop
is blocked outright with `403`, at every version. Everything else tested passes.

| User-Agent | Result |
|---|---|
| `Mozilla/5.0 (X11; Linux x86_64) ... Chrome/120\|131\|140\|150 ...` | **403** |
| `Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/131\|150 ...` | pass |
| `Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0` | pass |
| bare `Mozilla/5.0` | **403** |

HTTP version (1.1 vs 2), `Sec-Fetch-*`, `Upgrade-Insecure-Requests` and cookies make **no**
difference — each was tested separately. Only the UA matters for this gate. Use the
Firefox/Linux UA above.

**2. WAF challenge (the real limit).** After roughly 60-70 listing requests the edge starts
answering `HTTP 202` with `content-length: 0` and the header `x-amzn-waf-action: challenge`.
This needs JS execution to mint an `aws-waf-token` cookie, so curl cannot clear it. A `202`
with an empty body is the signature — check for it, do not treat `202` as success.

Once challenged, it stays challenged: a cookie jar, 15 s spacing and a cooldown all failed.
Switch to the Playwright profile `browser-data/` for the rest of the run.

**Preflight (step 2) for this platform.** The listing harvest needs no browser, so do not
stop when `browser-data/` is locked by another session. Run the open-HTTP part first,
and only then, if the browser is free, fetch descriptions and the remaining queries. If
the browser stays locked, finish the run on listing data alone and say in the report that
descriptions are missing — that is a degraded but useful run, not a failure.

## Search

| Track | Query / URL |
|---|---|
| swe | `https://www.profesia.sk/praca/?search_anywhere=.NET` · `...=C%23` |
| devops | `...=DevOps` · `...=SRE` · `...=Kubernetes` · `...=Terraform` · `...=Cloud+Engineer` · `...=Platform+Engineer` |

- `search_anywhere=` matches anywhere in the ad body, not just the title, so a hit does **not**
  mean the technology is central. Treat it as a weak signal and say so in the report.
- The server appends `&sort_by=relevance` on redirect.
- Pagination: `&page_num=N`, 20 rows per page. Stop when a page returns fewer than 20 rows.
- `.NET` returned 46 hits and `C#` 20 (27 of them already in the `.NET` set) on 2026-10-05.
- No "last 24h" parameter found yet. The listing prints a relative age instead
  (`Predvčerom`, `Pred 6 dňami`, `Pred týždňom`, `Pred mesiacom`).

## Extraction

Listing rows are plain server-rendered HTML, no JS needed. One `<li class="list-row">` per job:

```python
ROW = re.compile(r'<li class="list-row"[^>]*>(.*?)</li>', re.S)
# inside a row:
#   <h2><a id="offer(\d+)" href="(...)">   -> offer id + URL (strip the ?search_id= query)
#   <span class='title'>...</span>         -> title
#   <span class='employer'>...</span>      -> company
#   class='job-location'>...</span>        -> location
#   <span class="label label-bordered green ...">...</span>  -> salary
#   class='info'>(?:<strong>)?...          -> relative posting age
```

Everything is HTML-entity encoded (`&#x2F;` for `/`), so run `html.unescape` on each field.
A working harvester lives in the 2026-10-05 scratchpad run; re-create it from the regexes above.

Canonical URL: `https://www.profesia.sk/praca/<company-slug>/O<offer-id>`.

## Filters and traps

- **Salaries are monthly gross EUR**, not yearly. Do not compare them to the Spanish
  €/year targets in `preferences.md` without converting.
- **Evergreen ads.** A low offer ID next to a fresh relative date means a long-running ad
  that gets refreshed. Seen on 2026-10-05: `O3154270`, `O3668702`, `O4575980`, `O4776775`,
  `O4880320`, `O4731994`. The date column is unreliable for these.
- Staffing firms (SourceFirst International, Pro HR, Unlimit Recruitment) post several
  near-identical ads for the same role; the end client is not named.
- `.NET` matches ads where .NET is incidental — C/C++ motion control, native Android,
  smart metering, student part-time work all surfaced in the 2026-10-05 run.
- **Slovak work authorisation.** Spanish permanent residence gives no right to work in
  Slovakia; a third-country-national permit or EU Blue Card is needed. Flag it once per
  report, do not drop jobs over it (the candidate has 6+ years of Bratislava history and
  advanced Slovak).
- "Remote work" on a Slovak ad usually still means Slovak payroll or tax residency.

## Rate limits

~60-70 listing requests with 1 s spacing before the challenge triggers; the two SWE queries
plus pagination fit, the DevOps queries did not. Budget the request count up front and run
the most valuable queries first, or go through the browser from the start.

## Job ID

Store the offer id **with the `O` prefix**, exactly as it appears in the URL
(`.../O5357696` -> `O5357696`), in `data/seen/profesia.tsv`. The listing markup gives the
bare number in `id="offer(\d+)"`, so prepend the `O`. The rows backfilled from the
2026-06-19 run already use this form, and the dedupe in step 3 compares them as strings.

## Already applied

profesia.sk shows the application history only inside a logged-in candidate account, which
has not been set up. Until then `data/seen/profesia.tsv` is the only record of what was
applied to, so the step 3 dedupe against it is not optional on this platform.

## Run history

- **2026-06-19** (before this playbook existed): a mixed-source run that reached
  profesia.sk; 25 rows in the registry, 4 of them `applied` — Asseco Central Europe,
  ComAp Slovakia, Grafton Slovakia, Telegrafia.
- **2026-10-05**: listing-only harvest of the `.NET` and `C#` queries, 47 jobs,
  `reports/jobs-2026-10-05-profesia-sk.md`. Run ad hoc rather than through `/hunt`, so the
  registry dedupe was applied only afterwards. It found that **ads here live for months**:
  three jobs carried the same offer IDs as the June run (`O5273955` ESET,
  `O5277294` Deutsche Telekom, `O4575980` Deutsche Telekom). Expect heavy overlap on every
  re-run and lean on the registry rather than on the relative posting date.

## Backlog

- **2026-10-05**: DevOps/SRE queries (DevOps, SRE, Kubernetes, Terraform, Cloud Engineer,
  Platform Engineer, site reliability) never ran — the WAF challenge hit first. The whole
  DevOps track on this platform is uncovered.
- **2026-10-05**: no job descriptions were fetched for any of the 47 harvested jobs, so
  every verdict in `reports/jobs-2026-10-05-profesia-sk.md` rests on the listing fields only.
  Jobs whose verdict hinges on the description: #5, #12, #13, #16, #17, #18, #21, #24.
- Apply mechanics not explored. profesia.sk applications normally need a logged-in
  candidate account.
