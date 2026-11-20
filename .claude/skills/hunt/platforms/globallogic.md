# GlobalLogic careers (all countries)

> Last verified: 2026-10-23 · Access: open HTTP (server-rendered WordPress, no login) · Apply: no
> GlobalLogic (Hitachi) careers site: ~590 open roles worldwide, many remote in Ukraine, Croatia, Romania, Slovakia. Large .NET and support demand.

No browser needed: plain curl works. Do not use Playwright for this platform.

## Access

`curl -sL -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" <url>`
returns the full HTML (HTTP 200, ~220 KB per list page). No cookies, no captcha seen.

## Search

| What | URL |
|---|---|
| List, page 1 | `https://www.globallogic.com/ua/career-search-page/` |
| List, page N | `https://www.globallogic.com/ua/career-search-page/page/<N>/` |

- 10 cards per page; 59 pages on 2026-10-23. The last page number is the highest
  `career-search-page/page/<N>/` link on page 1.
- Newest first. A daily run can stop at the first page whose cards are all in the seen
  registry.
- The `/ua/` locale lists the global pool (Sweden, Croatia, India, ...), not only Ukraine.
- The filter form (`#job-filter`: `keywords`, `job_functions[]`, `experience[]`,
  `location[]`) is applied by JS; GET parameters were not verified. Paginate the full list.
- There is no Spain office in the location filter. Countries: argentina, canada, chile,
  colombia, croatia, germany, india, ireland, japan, mexico, peru, poland, romania,
  slovakia, sweden, ukraine, united-kingdom, united-states, uruguay.

### Parallel run (no Playwright)

The run is split into one subagent per list page, all in parallel (general-purpose agents,
curl only). Each one: fetches its page, prefilters the cards, fetches the detail page of
every surviving card, evaluates it per `.claude/agents/job-matcher.md` +
`preferences.md` + the CV, and returns compact JSON. The orchestrator merges the pages and
passes them to `report-writer`.

## Extraction

List page card:

```html
<a href="https://www.globallogic.com/ua/careers/<slug>-irc307341/" class="job_box">
  <div class="top_area">
    <span class="job_location">Ukraine</span>        <!-- 1..n, city then country -->
    <span class="job_tag">Remote</span>              <!-- Remote | Hybrid | On-site -->
  </div>
  <h4>Senior Python Developer IRC307341</h4>
</a>
```

Detail page (`section.career_detail_banner`):

- `.career_banner_sub_head`: "Published on 23 October 2026" (freshness).
- `.career_banner_code`: job code `IRC307341`.
- `.career_banner_details` pairs `<span>label</span><p>value</p>`: Function, Experience
  (e.g. "5-10 years"), Location, Skills, Work Model.
- The description (Requirements / Job responsibilities / What we offer) follows the banner.
  Strip tags and read the text after the `<h1>`.

## Filters and traps

- **One code, several countries.** The same IRC code is posted per country with slug
  suffixes `-2`, `-3` (`senior-devops-engineer-irc307205`, `-2`, `-3`). Treat each slug as
  its own posting (the location differs), report them together.
- **Country-bound remote.** "Remote" means remote inside the posting's country, on that
  country's payroll. A Ukraine / Croatia / Romania / India remote role is a country
  allowlist that excludes Spain: hard blocker, unless the text says EMEA / Europe /
  any location. Slovakia: open to relocation (see preferences.md), so not a blocker.
- Poland postings: excluded entirely (preferences.md).
- Germany and Sweden on-site/hybrid roles usually need local presence; Germany often
  German.
- Most roles are Senior / Lead and in embedded, automotive (AUTOSAR), DevOps, data:
  expect a low MATCH rate.
- The same roles also appear on Djinni (same IRC code in the title): cross-check
  `data/seen/djinni.tsv` by the IRC code.

- **List order is not stable** between requests: page 1 and page 2 overlapped on
  2026-10-23. Dedupe by slug after merging pages; a few postings may be missed.
- **Yield (first full run, 2026-10-23):** 586 postings, 0 MATCH, 0 WEAK. Filters: country-bound
  location 168, stale 122, Poland 122, Lead/Architect/Manager titles 103, DevOps/Cloud 48.
  The .NET roles that exist sit in India, Ukraine-only remote or LATAM. Pages past ~38 are
  older than 30 days. A daily run only needs the first ~10 pages.

## Rate limits

None seen at 59 list pages + several hundred detail pages fetched in parallel
(2026-10-23). Keep a short pause (0.5 s) between detail fetches within one agent.

## Merging worker results

Each worker's JSON array ends up in its subagent transcript. Rather than re-pasting them,
parse the transcripts: walk every string in the assistant messages and json-load the ones
that contain `"page"` and `"verdict"` (the hand-back is a tool input, not a text block).

## Job ID

The slug's trailing code with its suffix, lower-case: `irc307205-3` (from
`/careers/senior-devops-engineer-irc307205-3/`). Store in `data/seen/globallogic.tsv`.

## Already applied

No candidate account is used; rely on `data/seen/*.tsv`.

## Backlog

- Apply is not supported yet (the form sits at `#apply_now` on the detail page; not
  explored).
- Verify whether GET filter parameters (`?keywords=.net&location[]=slovakia`) narrow the list.
