# Amazon Jobs

> Last verified: 2026-07-30 · Access: open HTTP (public JSON) · Apply: no
> All Amazon/AWS openings in Spain through one public JSON endpoint, no browser and no login.

## Access

Plain curl with a browser User-Agent. No Playwright needed, so `job-finder` can do it.

## Search

`https://www.amazon.jobs/en/search.json?normalized_country_code[]=ESP&offset=0&result_limit=100&sort=recent`

- `result_limit` is at most 100; page with `offset`. `hits` gives the total.
- Category filter: `category[]=software-development`. Facets:
  `facets[]=normalized_country_code`.
- 2026-07-30: 281 jobs in Spain.

## Extraction

Every object already contains `title`, `city`, `job_category`, `posted_date`,
`job_path`, `description`, `basic_qualifications`, `preferred_qualifications`. There is
no need to open detail pages. The text contains HTML (`<br/>` and entities).

## Filters and traps

- **The whole European Sovereign Cloud / ESC / EUSC Managed Operations family** (10 jobs
  in Madrid, the closest stack match to the SAP DevOps experience: Linux, Terraform, IaC,
  SRE) says verbatim *"This role requires you to be a national of an EU member state"*.
  A Spanish permanent residence does not qualify. Filter them out until naturalisation
  (the full list is in `reports/jobs-2026-07-30-amazon-spain.md`).
- Reachable: generic SDE roles where C# is listed next to Java/C++ in the basic qualifications.
- Applied Scientist roles all require a PhD and publications.

## Job ID

`job_path` (or the numeric ID inside it).
