# remote.com

> Last verified: 2026-07-22 · Access: browser (guest) for search, open HTTP for job pages · Apply: no
> Job marketplace of an EOR platform; the .NET pipeline there was almost empty.

## Access

- `remote.com/jobs` is a Next.js SPA. curl/WebFetch do not see filtered results, so
  searching needs Playwright. `job-finder` cannot do it; collect in the main session.
- Job detail pages (`/jobs/<company>/<slug>`) return server HTML with a JSON field
  `"description":"..."`, so plain curl works for them.

## Search

`https://remote.com/jobs/all?query=<term>`. The parameter is `query=`, **not** `keywords=`.

- The search is loose full-text/substring: `C%23` also catches "C++" and "Cloud".
- Try broader terms too: `backend`, `software engineer`, `devops`.

## Filters and traps

- On 2026-07-22 the ".NET" / "C#" / "dotnet" results were almost entirely **one**
  recruiting-agency posting (Bluelight Consulting, "C# / DotNet Developer… Remote, Latin
  America") reposted about 20 times under different job IDs.
- remote.com is an EOR platform: a location tag "X only" is a legal hiring restriction,
  not a preference. For a Spanish resident, most .NET jobs there are unreachable.
- Tell the user about the reposts and the location filter explicitly; do not filter
  them out silently.

## Job ID

The `<company>/<slug>` path of the job page.
