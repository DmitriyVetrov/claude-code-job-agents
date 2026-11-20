# Djinni

> Last verified: 2026-10-29 · Access: browser (logged in) · Apply: yes
> Ukrainian IT board (djinni.co), lots of remote .NET and DevOps; the candidate is a native Ukrainian speaker.

## Access

- The logged-in session lives in the Playwright profile `browser-data/`.
- Check it by opening `https://djinni.co/my/inbox/`. A redirect to login means the
  session expired.
- Everything below can be done from inside the page with `fetch()` + `DOMParser`
  (same-origin, cookies included), which is much faster than clicking through pages.
  `browser_evaluate` / `browser_run_code_unsafe` can only save files inside the project;
  use `.playwright-mcp/` (gitignored), not the scratchpad.

## Search

| Track | URL |
|---|---|
| swe | `https://djinni.co/jobs/?primary_keyword=.NET&employment=remote&hide_contacted=true` |
| devops (Junior SRE only, since 2026-10-22) | `https://djinni.co/jobs/?primary_keyword=DevOps&keywords=SRE&employment=remote&hide_contacted=true` (not verified); keep only SRE titles |
| offer-max (since 2026-10-22) | `primary_keyword=QA`, `primary_keyword=Support` with `&exp_level=no_exp` / `1y` (not verified) |

- `hide_contacted=true` hides jobs the account already applied to. Keep it on.
- Paginate with `&page=N`. On 2026-10-04 `.NET` had 3 pages (41 postings) and `DevOps`
  had 8 pages (115 postings; it was 9 pages on 09-30, applied jobs drop out).
- **A page past the last one does not 404.** It returns a fallback list of unrelated jobs
  (designers, SEO, founders) that is identical for every category. Stop at the largest
  `page=N` found in the pagination links (`a[href*="page="]`), or at the first page with
  fewer than 15 cards.
- **Region filter**, server side, removes the Ukraine-only noise: `&region=eu` (cards that
  say "EU" or "Countries of Europe or Ukraine") and `&region=worldwide`. Send them as
  separate requests: several `region=` values in one request combine as AND, not OR.
  `region=other` is a no-op. `&country=ESP` finds postings that name Spain (0 for .NET,
  1 or 2 elsewhere). Only about 12 of 41 .NET postings were open to Europe/Worldwide.
  `region=eu` is loose: it also returns Ukraine-only and "Poland, Romania, Ukraine" cards;
  `worldwide` results are a subset of `eu` (2026-10-23).
- **Keyword search** (verified 2026-10-23): `keywords=` is ignored (full unfiltered list).
  The real params are `all_keywords=` (+ `search_type=basic-search|full-text|title-only`),
  `any_of_keywords=`, `exclude_keywords=`, `q_company=`. The AI category is
  `primary_keyword=ML%20AI` (label "ML / AI"); `Data Science` is separate. An unknown value
  such as `AI/ML` silently returns the whole unfiltered list, not a 404.
- **Daily sweep (2026-10-29)**: 41 feeds in one `browser_evaluate` with in-page `fetch` + `DOMParser`
  (`.NET`/`Fullstack`/`DevOps` × `region=eu|worldwide` remote; `QA`/`Support` × `exp_level=no_exp|1y` ×
  region; `.NET` remote; `country=ESP` × 13 categories with/without `employment=remote`), 53 requests,
  ~180 cards, keep them in `window.__dj` and dump only the unseen ones.
- **Freshness**: a card bumped "updated today" can be months old. Read "Published D Month" on the job
  page before applying (IvaTech QA: published 18 June, 153 applications → stale).
- **Dates**: cards show only "updated Nh ago"; the job page shows "Published D Month" (year
  only if not the current one). JSON-LD `datePosted` is the bump time, not publication.
- **There is no SRE category.** SRE belongs to `DevOps`. Full-text
  `/jobs/?keywords=SRE` returns irrelevant noise.
- The umbrella `.NET` category holds nearly all .NET work. The sub-categories (`.NET Gamedev`,
  `Dotnet Web`, `ASP.NET`, `Blazor`, `Dotnet Cloud`, `MAUI`, `Xamarin`, `Dotnet Desktop`) were
  empty with the region filters. `MS Dynamics` and `ERP` returned only functional-consultant
  roles. `Fullstack` (with `region=eu` / `worldwide`) surfaces extra .NET + React postings
  (outstaff agencies); screen it by title/description for C#/.NET. `Sysadmin`, `Security`
  and `Data Engineer` are off-track, but a few DevOps-titled postings are filed there.
- Dynamics (C# + ERP), MAUI and Creatio postings are in scope at junior+/middle (see
  preferences.md). Look for them in the .NET results.

### Card selectors (search results)

- Card: `.job-item`, `id="job-item-<jobId>"`; title link `a.job_item__header-link`
  (`href` has the slug).
- `header.textContent` lines are title, company, salary tag.
- Location / experience / English / domain row: `.location-text` → `closest('.d-flex.flex-wrap')`,
  e.g. `Full Remote · Countries of Europe or Ukraine · 3 years of experience · English - B1 · SaaS`.
- Full description: `.js-original-text` (the card also has a truncated `.js-truncated-text`).
  The card already carries the full text, so no second request per job is needed.
- The `$ / $$ / $$$ / $$$$` tag is a salary level **relative to other jobs** (tooltip:
  $ below average, $$ around, $$$ above, $$$$ top range), not an amount. A real number
  appears only when the employer discloses it ("to $1000").

## Filters and traps

Most common skip reasons, from about 270 postings screened on 2026-10-04 (and 115 on 09-30):

- **Country restrictions** (the largest group): Ukraine / Poland / Georgia / Germany-
  Austria only. Some state "Applications from Spain are not accepted". **Poland is
  excluded entirely.** The location row on the card is the quickest check: keep
  "Europe", "EU", "Worldwide" or a list that includes Spain.
- **English C1 required** (the profile is B2). Visible on the card row.
- Architect / Tech Lead / Team Lead titles. Senior titles in the DevOps track.
- A whole unfamiliar platform as the core: Creatio at Senior level, FreeSWITCH / SIP /
  VoIP telecom, network engineering (Cisco), data-center racks, cPanel web hosting,
  automotive domain, Python/Scala/Go/Java as the primary language, Node.js/NestJS backend.
- Not a job: paid "consultant" gigs to interview other candidates for an agency.
- Salary ceiling far below expectations with no flexibility signal ("to $1000", "to $1500").
- Several postings from the same employer: apply to one per pass. Outstaff agencies (for
  example A-LISTWARE) post the same client role 2-3 times with different titles.
- **Recruiter quiz.** Some postings add mandatory screening questions to the apply form
  (a Yes/No radio such as "at least 3 years as DevOps?", or a free-text one such as
  notice period). Read them before filling anything. If the honest answer would knock the
  candidate out, or the wording cannot be answered from the CV ("outstaff project with a
  client-side team?"), do not submit; list the job under Needs manual review.
- **Salary warning.** When the profile expectation is above the job's budget, the page and
  the form show "You expect a higher salary than the job is going to pay" (range often
  undisclosed). Do not submit the default silently; flag it.
- Some postings need a second step outside Djinni after the application (AgileEngine
  sends the candidate to its own "LaunchPod" site).

## Rate limits

None observed: 16 applications on 09-30, 3 applications on 10-04, plus about 300 page
fetches in two scripted sweeps at 300-400 ms spacing.

## Job ID

The numeric ID in the job URL `https://djinni.co/jobs/<id>-<slug>/`.

## Already applied

- `hide_contacted=true` in the search URL (hides the exact posting only, not other
  postings of the same employer).
- Inbox buckets, each paginated with `&page=N` (a page past the end repeats page 1):
  - `https://djinni.co/my/inbox/` active threads (a thread appears here once the recruiter
    has reacted);
  - `https://djinni.co/my/inbox?bucket=apply`, "Waiting for an answer": **applications
    nobody has answered yet live here**, so this is where recent applications show up;
  - `?bucket=unread` and `?bucket=archive` (2 pages, 45 threads on 2026-10-04).
  `?bucket=waiting` is not a valid name and silently shows the default view.
- Build the company blocklist from all of them before applying: parse each thread's
  `Company · Recruiter · Title` text.
- A second application to an employer that already has a thread (different role) lands in
  the same recruiter thread, and the thread title changes to the newest role. Djinni shows
  "You have a conversation with this recruiter already" on the job page.

## Apply

Flow (verified on 2026-10-04, 3 submissions):

1. Open the job page. Click the first "Apply for the job" button. The form `#apply_form`
   is `display:none` until then.
2. `textarea#message`: the cover message (fill it in one go).
3. CV: `select[name=cv_file_upload_id]` is a Tom Select with three options: the SWE PDF,
   the SRE-DevOps PDF, and "Don't share". The SWE PDF is preselected, so **always set it per
   track**: `select.tomselect.setValue(<option value>)` (setting `select.value` alone does
   not update the widget). Read the option values from the page; do not hard-code them.
4. Salary: a row "Salary expectations" shows the profile default (currently $3000) with a
   "Change for this job post" toggle that reveals `input[name=salary_changed]` (step 50).
   Some postings have no salary row at all; state the rate in the message then.
5. Quiz fields, when present: `input[name=quiz_id]` plus `answer_<n>` radios or text inputs.
   Dump them (`form.querySelectorAll('[name^=answer_]')` with their labels) before submitting.
6. Submit with `#job_apply`. Success is the URL parameter `?applied=ok` plus the page text
   "Djinni has sent your application to the employer". The new thread then appears under
   `?bucket=apply`.

Verified again 2026-10-22 (4 submissions):

- Playwright `click()` on the apply button and on form links times out (element reported not
  visible). Click through `browser_evaluate` instead: `button.js-inbox-toggle-reply-form`
  opens the form, `#job_apply` submits. The page then redirects to `?applied=ok`.
- Salary: click the "Change for this job post" link, then set `input[name=salary_changed]`
  (dispatch `input` and `change`). A posting with a cap shows "requires candidates with salary
  expectations up to $N".
- **Stored CVs** live at `https://djinni.co/my/account/` (block `#profile_cv_block`, up to 5).
  Upload: click "+ Upload CV" through `browser_evaluate`, click `input.js-cv-file-input`, pick the
  PDF with the file-chooser tool, then press `[name=save_changes]` (it saves the whole account
  form with its current values). Cards `#uploaded_cv_<id>` have "Set as default CV" and
  "Remove from profile" (soft: the file stays for links already shared). Avoid "Delete file"
  (hard delete, breaks shared links). On 2026-10-22 the old files were replaced by the
  current per-track versions.
  Uploading without the file chooser works: `setInputFiles` on `input.js-cv-file-input`
  after clicking "+ Upload CV", then `[name=save_changes]`, one file per save.
- **CV: use the one stored in the account** (`select[name=cv_file_upload_id]`, preselected);
  do not upload new files (user rule, 2026-10-22). "+ Upload CV" opens a file input that
  needs the file-chooser tool: avoid it.
- The job page's description (`.js-original-text`) is often empty in a fetched copy; the
  schedule or shift lines are at the end of the text, so read the whole posting before
  applying.

Content rules:

- In messages say only "based in Spain", never a city (user rule, 2026-10-22).

- Write a **cover message** tailored to the posting. Where the fit is a stretch (for example
  AWS-heavy roles against an Azure-first background), say so honestly instead of overclaiming.
- For junior roles, and for DevOps roles written "Middle/Senior", disclose the real
  seniority from the CV; never round years of experience up.
- When the posting asks for location, rate and contract type, give them in the message.
  Do not make personal commitments the CV does not state (on-call rotations, shifts,
  working hours in another timezone); flag those jobs for manual review instead.
  Exception (user rule, 2026-10-23): night shifts and 24/7 rotation are accepted for junior
  support / offer-max roles, and a low salary cap is never a reason to hold (preferences.md).
- **Salary: use the local market of the board, not your home-country rates** (the number lives in
  preferences.md). A figure derived from a Western hourly rate gets the candidate filtered out.
- Pick the CV by track (preferences.md).

## Salary analytics (optional)

`https://djinni.co/salaries/` accepts GET parameters:
- `category`: for example `dotnet`, `dev_ops`, `sysadmin` (values from `select[name=category]`)
- `exp`: `0` (<1 y), `1` (1-2), `2` (2-3), `3` (3-5), `5` (5+)
- `region`: `UKR`, `ESP`, `eu`, `other`, …; `work_format=full_remote`; `english_level`;
  `employment` seems to be ignored.

Fastest route: in `browser_evaluate`, `fetch(url)`, parse it with `DOMParser`, and
regex the `textContent` for `Expectations avg`, `Salary range avg`,
`Median salary of hired candidates`, `Candidates online`, `Jobs online`,
`Job applications avg`. For SRE salaries specifically, cross-check DOU's half-yearly
report (dou.ua/lenta/articles/salary-report-devops-*), where SRE is a separate line.

## Backlog

- Shortlisted jobs that were not submitted are stored as `backlog` rows in
  `data/seen/djinni.tsv` (as of 2026-10-04: five MATCH jobs waiting for the candidate's
  decision on a screening question, on-call or EST hours, or a salary figure). Put them
  first on the next run and check they are still open.
- Both category lists were screened to the last page on 2026-10-04.

## Follow-ups in existing threads

Verified 2026-10-13 (7 messages sent).

- A thread page `/my/inbox/<threadId>/` always carries a reply form
  (`form.js-inbox-reply-form`, `textarea[name=message]`, submit `button.reply-form-submit`),
  including threads in `?bucket=apply` that the recruiter has never answered.
- Sending without clicking: POST to `/my/inbox/<threadId>/` with
  `csrfmiddlewaretoken` (from the `csrftoken` cookie) + `message`, headers
  `X-CSRFToken` and `HX-Request: true`. Returns 200; re-fetch the thread and check
  the last `.thread-message` to confirm. ~1.2 s spacing was fine for 7 in a row.
- Thread history parses as `.thread-message` → `.font-weight-500` (author),
  `.col-auto` (relative age, e.g. `11d`, `Edit 0m`), `.thread-message-body` (text).
  That beats reading the blob `textContent`, which buries the tail under inline scripts.
- Who owes whom an answer: in the inbox list the last-message preview is prefixed
  `You:` when the candidate wrote last. `You sent application` means the recruiter has
  never replied. "Your application for this position has been declined" is a rejection.
- Before writing a follow-up, read the whole thread. Common traps:
  a recruiter template that is really a soft rejection ("if we don't contact you, we went
  with other candidates" — BetterMe); an unanswered screening quiz (answer it, don't nudge);
  a thread already nudged two or three times; an `· Offline` job title, where the posting is
  closed and the useful ask is about other openings instead.
- **Editing a sent message** (verified 2026-10-22): the candidate's own `.thread-message` has an
  `a.edit-btn` ("Edit 5m" in the age column). Click it via `browser_evaluate`: the reply form
  `form.js-inbox-reply-form` loads with the old text in `textarea[name=message]` and a hidden
  `edit_id`; change the text, click `[type=submit]` (labelled "Save"). The thread keeps one
  message (no new one is sent). Thread IDs: `/my/inbox/?bucket=apply` lists them as
  `/my/inbox/<threadId>/`. An attached CV cannot be changed this way.
- Mirror the thread's language (Ukrainian with Ukrainian recruiters, English otherwise)
  and never add commitments the candidate has not made himself.
