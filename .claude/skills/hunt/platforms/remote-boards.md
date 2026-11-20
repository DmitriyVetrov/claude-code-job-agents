# Remote boards (RemoteOK, Remotive, We Work Remotely, LandingJobs, euremote)

> Last verified: 2026-06 (the original job-finder pipeline) · Access: open HTTP (APIs / RSS) · Apply: no
> Global remote boards with public feeds; cheap to pull, so `job-finder` can do this run on its own.

Delegate this run to `job-finder`: no browser is needed. Tell it to Read this file.

## Search and extraction

Use curl with a browser User-Agent, for example
`curl -s -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" <url>`.

| Board | Endpoint | Fields |
|---|---|---|
| RemoteOK | `https://remoteok.com/api?tag=dotnet`, `?tag=csharp` (JSON; the first element is a legal notice, skip it) | position, company, location, tags, description, url, salary_min/max |
| Remotive | `https://remotive.com/api/remote-jobs?search=.net&limit=50` (also `?category=software-dev`) | title, company_name, candidate_required_location, url, description |
| We Work Remotely | RSS `https://weworkremotely.com/categories/remote-programming-jobs.rss`, `/remote-back-end-programming-jobs.rss`, `/remote-devops-sysadmin-jobs.rss` | title, link, description |
| LandingJobs | `https://landing.jobs/api/v1/jobs` (tag/location filters; EU focus). If the API does not respond, WebFetch the search page. | title, company, location, url |
| euremote.io | Look for RSS (`/feed`, `/rss`) first; otherwise WebFetch the page and extract the jobs. | title, company, url |

| Track | Keywords / tags |
|---|---|
| swe | dotnet, .net, c#, csharp, asp.net, backend |
| devops | devops, sre, kubernetes, terraform, cloud |

## Filters and traps

- `candidate_required_location` (Remotive) and the location text (RemoteOK) are often
  "USA only", "Americas" or "LATAM". Check them against the geo rules in preferences.md.
- The same job often appears on several boards. Merge by company + title and list all sources.
- **Drift seen 2026-10-23** (ai-market run):
  - Remotive API is effectively dead: every search and category returns the same 9-job
    delayed sample. RSS `/remote-jobs/feed` gives 10 items; `ai-ml` and `software-dev`
    category slugs 404; the HTML listing is JS-rendered.
  - RemoteOK: `?tag=dotnet`, `csharp`, `llm` and the other AI tags return only the legal
    notice; `?tag=ai` has stale dates. Pull the untagged `/api` and `?tag=python`,
    `engineer`, `dev`, `backend`, then filter by keyword locally.
  - WWR: RSS descriptions hold the full text; title is "Company: Title". The category is
    unreliable (AI roles filed under Design or Product), so pull every category feed.
    `search.rss` returns 406. The region says "Anywhere" even when the text says
    Remote - US: read the text.
  - LandingJobs API returns at most 50 jobs, mostly onsite Portugal. euremote.io was
    unreachable (curl 000).

## Job ID

`<board>:<id or url>` (RemoteOK `id`, Remotive `id`, RSS `guid` or link).
