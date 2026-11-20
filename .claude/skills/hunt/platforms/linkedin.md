# LinkedIn

> Last verified: 2026-11-18 · Access: browser (logged in); open HTTP guest endpoint as fallback · Apply: yes (Easy Apply only)
> Biggest volume of relevant .NET and DevOps roles in Spain; Easy Apply submits in-page.

**Default: the logged-in browser** (visible Chrome through Playwright, the user's own
session), for report-only runs too. Only the browser gives the personal
recommendations, the Easy Apply filter and "Viewed"/"Applied" marks on cards. The
**guest endpoint** is the fallback when Playwright MCP is not connected or the session
has expired and the user is not around to log in; say in the report that it ran in
guest mode (no recommendations).

## Access

- The logged-in session lives in the Playwright profile `browser-data/` (verified
  2026-09-10 and 2026-10-01). Check by opening `https://www.linkedin.com/feed/`. An
  authwall or login form means the session expired; ask the user to log in.
- **Guest endpoint** (no login, no account risk):
  `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=<kw>&location=<loc>&f_TPR=<window>&start=<N>`
  10 cards per request; paginate `start` in steps of 10 until an empty response. Works
  with curl/httpx and with `browser_context.request.get`.
- **Environment quirk:** requests to linkedin.com from background processes
  (`nohup … &`, `run_in_background`) hang silently, with no timeout and no response.
  Other sites work in the background. Run LinkedIn fetches in the foreground (a Bash
  call of up to ~110 s), in chunks, with resume state in a JSON file on disk.
- The logged-in `linkedin.com/jobs/search` opened from a headless profile hits the
  authwall. Use the visible Playwright browser.
- **No `bs4` in the system Python** (2026-10-04). The stdlib `html.parser.HTMLParser`
  works with the selectors in "Extraction" (a `div` with class `base-card` and a
  `data-entity-urn`; `h3.base-search-card__title`; `h4.base-search-card__subtitle`;
  `span.job-search-card__location`; `time[datetime]`). Titles often contain `|`
  ("Programador Senior .NET | Híbrido Madrid"), so hand cards to other tools as TSV, not
  pipe-separated text.

## Search

**Always wrap the phrase in URL-encoded quotes.** `keywords=.NET` without quotes is
read as almost "any job": the `.` is ignored and you get Junior UI / Cybersecurity /
Data / Support noise. `keywords=%22.NET%20Developer%22` is precise (verified 2026-07-20).
The same goes for `%22C%23%20Developer%22`.

| Track | Phrases |
|---|---|
| swe | `%22.NET Developer%22`, `%22C%23 Developer%22`, `%22.NET Engineer%22` (~80 each, 1 week, Easy Apply), `%22Backend Developer%22 .NET` (162), `%22Application Support%22` (250, broad: mostly non-.NET); swept 2026-10-22 |
| devops (Junior SRE only, since 2026-10-22) | `%22Junior Site Reliability%22`, `%22SRE%22 junior` (not swept yet). No DevOps / Cloud / Platform phrases. |
| offer-max (since 2026-10-22) | `%22Junior QA%22`, `%22Soporte técnico%22`, `%22Helpdesk%22`, `%22Junior Developer%22`, `%22Technical Support%22`; with `location=Madrid` and Valencia/Alicante (not swept yet) |

LinkedIn matches "C#/.NET Developer" under ".NET Developer", so the two swe phrases
overlap a lot. Dedupe.

URL parameters (logged-in `https://www.linkedin.com/jobs/search/?…`; the time and sort
parameters also work on the guest endpoint):

- `f_TPR=r86400`: last 24 h (**daily run**). `r604800`: one week. `r2592000`: 30 days.
  Any number of seconds works (`r345600` = 96 h, used to cover a 3-day gap since the
  previous run). Size the window to the gap, not larger.
- `sortBy=DD`: newest first.
- `f_AL=true`: Easy Apply only. **Not reliable**: roughly 1 in 5-8 results opens with
  only an external "Apply" button ("Responses managed off LinkedIn").
- `location=Madrid` filters correctly. **`location=Valencia` and an explicit `geoId`
  for Valencia silently return the same set as no location at all.** Workaround: drop
  `location` (it defaults to a Spain-wide search, which returned more results: 21 vs 14
  for one keyword) and classify each card's own location text yourself (Madrid /
  Valencia-Paterna / remote Spain / other). Sanity-check any location filter with a
  control query before trusting it.
- Long form of the location parameter: `location=<City>%2C%20<Region>%2C%20Spain`.

### Recommended jobs (logged-in only)

`https://www.linkedin.com/jobs/collections/recommended/` ("Top job picks for you",
"based on your profile, preferences, and activity like applies, searches, and saves").
Collect it with the paginated snippet in **Extraction**.

Measured on 2026-10-04: 60 unique jobs over 4 pages. Only **3 of the 60** were in a
guest keyword sweep of the same day (8 phrases, 96 h window, 1,029 cards), and only 2
were in the seen registry. So this is a separate source, not a duplicate:

- it finds jobs without the keywords in the title ("Senior Developer", "API Engineer",
  "CloudOps Engineer", "Integration Developer Azure Platform");
- it keeps jobs older than the daily time window.

By title, roughly two thirds were on-profile (~20 .NET, ~13 DevOps/Cloud, 4 AI).
Caveats:

- All 60 cards were marked **Promoted** (paid placement).
- The feed follows recent activity: after 8 Barcelona applications on 2026-10-01,
  ~25 of 60 were in Barcelona.
- It is steered by the profile's Open to Work settings (see the end of this file).
  Filter it with preferences.md like any other source.

### Daily recipe (browser)

1. Check the session (`/feed/`).
2. Collect the recommendations (all pages).
3. For each phrase of the track, open
   `https://www.linkedin.com/jobs/search/?keywords=<phrase>&f_TPR=<window>&sortBy=DD`
   with no location, size the window to the gap since the last run, and run the
   extraction snippet. Classify locations from the cards.
4. In apply mode, add `&f_AL=true`.
5. Pause ~3 s between page loads. No limit was hit in a 42-application session, but
   this is the user's real account: do not hammer it.

### Fallback recipe (guest)

Without the browser: for each phrase, run the guest endpoint with
`location=Spain&f_TPR=<window>`, paginate to the end with 1.5-2 s pauses, and classify
locations from the cards.

## New search UI (since ~2026-10-22)

- `/jobs/search/?…` now redirects to **`/jobs/search-results/?…`**. Class names are
  obfuscated (`kxh…`); the old `a.job-card-container__link` selectors find nothing.
- Cards: `[componentkey^="job-card-component-ref-"]`; the job ID is the componentkey
  suffix. Parse `innerText` lines: drop a first line that ends with "(Verified job)" or
  starts with "Selected,"; then title, company, location, then footer flags (Viewed,
  Easy Apply, Promoted, posted time). On some cards the title line repeats: if
  title == company, shift by one (company is the next line, location the one after).
- Pagination: the "Next" button click does not load the next page reliably. Use the
  URL parameter **`&start=0,25,50,…`** (25 cards per page) and stop when a page adds no
  new IDs. Cap ~250 per phrase. The result count text is often missing.
- The recommended collection (`/jobs/collections/recommended/`) still uses the old
  layout and the old snippet below (142 jobs over 6 pages on 2026-10-22).
- `browser_run_code_unsafe` has no `require` (no fs). Results do not survive in
  `localStorage` across LinkedIn navigations. Working pattern: navigate in a second tab
  (`page.context().newPage()`), keep results in `window.__hunt` of the first tab, then
  dump with `browser_evaluate` + `filename:`. Script files for `filename:` must be under
  the repo (allowed roots), e.g. `.playwright-mcp/hunt/`.
- **Descriptions:** `page.request.get` of the guest `jobPosting/<id>` endpoint with the
  logged-in cookies returns a page without the description. Plain `curl` (no cookies,
  desktop UA) of `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>` works:
  ~360 in a row at 1 s pauses, no 429 (2026-10-22). Text is in
  `.show-more-less-html__markup`, criteria in `.description__job-criteria-item`.

- **Slovakia (2026-11-18):** guest `location=Slovakia` works (133 cards over 5 swe phrases,
  30-day window). Search 429-ed after ~30 requests, and `jobPosting/<id>` then 429-ed
  after 10-16 requests even after a 2-minute pause. Reading the job pages in the logged-in
  browser worked instead: `browser_run_code_unsafe` with a second tab, 18 jobs per call
  (`/jobs/view/<id>/`, 2.5 s settle + 1.5 s pause, slice `innerText` after "About the
  job"), results kept in `window.__hunt` of the first tab, then dumped with
  `browser_evaluate` + `filename:`. 54 jobs, no block. For Slovak runs, title-filter
  first: about half the cards are SAP/ABAP, Workday, German-speaking or Lead roles.

## Extraction

**Guest endpoint HTML: parse with BeautifulSoup, never regex.** A regex on
`<div class="base-card…">` silently returns 0 cards. Per `li`:
`.base-search-card__title`, `.base-search-card__subtitle` (its nested `a` is the
company link), `.job-search-card__location`, `a.base-card__full-link` (job URL),
`time[datetime]` (posted).

**Logged-in list pages** (search results and the recommended collection): the list is
virtualised and `browser_snapshot` is expensive (hundreds of "similar jobs" nodes).
Use one `browser_evaluate`. This snippet scrolls each page and follows
"View next page" (verified on the recommended collection, 2026-10-04):

```js
async () => {
  const sel = 'a.job-card-container__link, a.job-card-list__title';
  const out = new Map();
  const grab = () => {
    for (const a of document.querySelectorAll(sel)) {
      const li = a.closest('li');
      const id = (a.href.match(/\/jobs\/view\/(\d+)/) || [])[1] || li?.getAttribute('data-occludable-job-id');
      if (!id || out.has(id)) continue;
      const company = li?.querySelector('.artdeco-entity-lockup__subtitle, .job-card-container__primary-description');
      const loc = li?.querySelector('.job-card-container__metadata-item, .job-card-container__metadata-wrapper li, .artdeco-entity-lockup__caption');
      const foot = li?.querySelector('.job-card-container__footer-wrapper, .job-card-list__footer-wrapper');
      out.set(id, { id,
        title: (a.getAttribute('aria-label') || a.textContent).trim().replace(/\s+/g, ' ').replace(/ with verification$/, ''),
        company: company?.textContent.trim().replace(/\s+/g, ' '),
        loc: loc?.textContent.trim().replace(/\s+/g, ' '),
        foot: foot?.textContent.trim().replace(/\s+/g, ' ').slice(0, 80) });
    }
  };
  for (let page = 0; page < 4; page++) {          // raise the cap for long searches
    // Scroll in ~1200px steps; jumping straight to the bottom stalls at ~12 of 21 cards.
    let el = document.querySelector(sel);
    while (el && el.scrollHeight <= el.clientHeight + 10) el = el.parentElement;
    for (let last = -1, i = 0; el && el.scrollTop !== last && i < 40; i++) {
      grab(); last = el.scrollTop; el.scrollTop += 1200;
      await new Promise(r => setTimeout(r, 1100));
    }
    grab();
    const next = document.querySelector('button[aria-label="View next page"], .jobs-search-pagination__button--next');
    if (!next || next.disabled) break;
    next.click();
    await new Promise(r => setTimeout(r, 3000));
  }
  return { count: out.size, jobs: [...out.values()] };
}
```

- Without scrolling only ~6-7 cards render. Keep the scroll loop inside one `evaluate`
  (an internal `for` plus an `await` sleep). That takes far fewer round-trips than
  separate scroll, wait and extract calls.
- `foot` carries the card flags: `Viewed`, `Promoted`, `Easy Apply`,
  `Be an early applicant` (and presumably `Applied`, not seen yet).
- The `aria-label` of the title link holds the clean title. Its text node may repeat the
  title or add "with verification".
- For a long result list, pass `filename:` to `browser_evaluate` and decode the JSON
  string with Python.

## Filters and traps

- `f_AL=true` lies sometimes (see above). The same role from the same company can have
  Easy Apply on one posting and not on another (NTT DATA: the Barcelona posting yes,
  the Madrid one no).
- A closed posting shows either "No longer accepting applications" or (2026-10-23, external
  and some Easy Apply jobs) "Not currently accepting applications" with no Apply button at
  all. Match both when re-checking a backlog.
- ".NET" in the title does not guarantee a fit: for example an architect role that
  requires the INTEX platform and structured-finance domain. Read the description.
- "Cloud Engineer" postings can be **Genesys Cloud** (a contact-center platform), not
  cloud infrastructure.
- Jobs for a specific company: a keyword plus region search **misses** postings
  without your keywords in the title. For a per-company check run
  `keywords=<company name or handle>&location=Spain`.
- Match a job to a company **by the LinkedIn handle from the company's website**, not by
  name. Strip the suffixes `hr, rrhh, careers, jobs, talent, group, grupo, espana,
  spain, iberia` from the slug and compare the cores (the site links
  `company/edicom`, while jobs are posted by `edicomgroup-hr`). A name-only match is
  UNCERTAIN; use the stop-list from `industrial-parks.md`, otherwise
  "CSL Communications **Iberia**" catches the airline Iberia's jobs.

## Rate limits

- Guest endpoint: ~30-60 requests in a row with 1.5-2 s pauses pass. A burst without
  pauses gets HTTP 429, which clears after a few minutes.
- The search and `jobPosting/<id>` endpoints are limited separately (2026-10-23): search
  429-ed after 178 requests in ~10 min at 1.8 s pauses, while `jobPosting` right after
  took 58 requests at 2.5 s with no 429. Keep a sitting under ~150 search requests.
- Guest search always returns 10 cards per page, padding with fuzzy matches when a
  quoted phrase has few real hits ("MCP": 57 cards, 1 relevant). Card counts are not a
  relevance measure; filter by title. `location=European Union` mixes PT/IT/PL/LT and
  some US-metro roles.
- The company on a card can be a repost account ("FDE Times" carries OpenAI/Salesforce
  postings verbatim) or a recruiter hiding the client (Joppy, Robson Bale, Trust In SODA).

## Job ID

Numeric ID from `/jobs/view/<id>/`. On guest cards it is the trailing number in the
`a.base-card__full-link` slug (also in `data-entity-urn="urn:li:jobPosting:<id>"` on
the card).

## Already applied

Job Tracker: `https://www.linkedin.com/jobs-tracker/?stage=applied`. Click the
"Applied · N" filter chip; each job shows "Applied just now / Xm ago". The count went
163 → 196 during the 2026-10-01 run.

## Apply (Easy Apply)

Only jobs with an in-page **Easy Apply** button. Skip jobs whose only option is an
external "Apply" that leaves LinkedIn. Jobs from a partner ATS
(`applicantTrackingSystemName=Lever` in the URL) still open as a normal in-page Easy
Apply modal; no special handling is needed.

1. **Check the button on the job page first**:
   `Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Easy Apply'))`.
   If it is absent, skip the job.
2. **Open the modal** by clicking that button through `browser_evaluate`. A
   `browser_click` ref often dies on the page's own re-render.
3. **Read each step** with `browser_snapshot` saved to a file (`filename:`), then
   grep/Read only the `dialog [ref=…]` block. The dialog is a small prefix of the file.
4. Typical steps: (1) contact info: email prefilled, phone country code usually prefilled
   to Spain, the mobile number often empty and needs typing; (2) resume selection;
   (3) screening questions (0 to ~6 fields; sometimes skipped); (4) review and submit.
5. **Resume radio** (which file for which job: preferences.md): LinkedIn pre-checks whichever CV was used in the **previous**
   application, not the newest upload. Always check which radio is `[checked]`. Switch
   with `document.querySelector('input[type=radio][aria-label="<exact CV filename>.pdf"]').click()`
   via `browser_evaluate`. Use the precise `input[type=radio][aria-label=…]` selector:
   the wrapper `div` with the same aria-label may match first and does not pass the
   click on. `browser_click` on the ref often times out ("waiting for element to be
   visible, enabled and stable").
6. **Yes/No radios:** select `input[type=radio]` filtered by a substring of its
   `aria-label` and `.click()` index 0 (Yes) or 1 (No). Yes has always been the first in
   the DOM. Location questions ("Do you live in Madrid?", "commutable distance") were
   answered "No" before 2026-10-22, and LinkedIn prefills that: re-answer per
   preferences.md. `browser_fill_form` with `type: "radio"` fails ("Not a checkbox or radio
   button") because the ref points to a wrapper `div`.
7. **Dropdowns (`<select>`)** go only through `browser_select_option` or
   `browser_fill_form` with `type: "combobox"`. Setting `.value` in `evaluate` and
   dispatching `change` does not reach React state; the form then fails at Review with
   "Invalid input" or an empty required field.
8. **Salary / number fields** reject ranges and currency text ("40000-55000 EUR" gives
   "Invalid input" even under the character limit). Enter a bare integer such as
   `45000`. The error shows up as a `paragraph: Invalid input` next to the textbox.
9. **Prefilled answers** come from earlier applications whenever the question text
   matches verbatim (a "years with Google Cloud" value came from another company's form).
   Verify every prefilled value.
10. **Review page:** "Follow company" is pre-checked. Uncheck it, then click
    "Submit application". Both can go in one `evaluate`.
11. **Confirm success:** the dialog closes and the URL drops its
    `?companyName=…&trackingId=…` query back to the bare `/jobs/view/<id>/`. The Easy
    Apply button is also gone. Cross-check the whole batch in the Job Tracker at the end.

**Changes seen on 2026-10-22:**

- The modal is a native `<dialog>` element (not `[role=dialog]`); class names are
  obfuscated. Steps show "N/M pages".
- Radio questions: the question text is the `aria-label` of every radio in the group,
  and the option text ("Yes"/"No"/"Sí") is in `radio.parentElement.parentElement.innerText`.
  The resume radios have the file name as `aria-label`.
- The Easy Apply control can be a `<button>` **or an `<a>`** with the text "Easy Apply"
  (href = the job page itself; clicking opens the modal). Match both.
- **Daily Easy Apply limit:** after ~37 submissions in one evening LinkedIn showed a
  dialog "You reached today's Easy Apply limit … continue applying tomorrow" (only a
  "Got it" button). Stop the run, put the rest in `backlog`.
- Number fields reject words ("Inmediata" → "Invalid input", shown as plain text, not in
  an error class). Use digits (`0` for "start date in days").
- SmartRecruiters-backed forms (8 pages) prefill a location typeahead from the old
  profile ("Valencia"): retype "Madrid" and pick "Madrid, Community of Madrid, Spain".
  They end with a privacy-notice checkbox that must be ticked.
- Working helper set (inspect / auto-advance / radio / text / CV / submit) injected with
  `page.context().addInitScript` survives navigation; one `browser_run_code_unsafe` call
  can then open a job, pick the CV and stop at the first page with questions. ~40
  applications took ~1.5 h this way.

**Saved helper (2026-10-29):** `.playwright-mcp/hunt/ea.js` (gitignored) injects `window.__open`,
`__auto(cv)`, `__radio(qRe, optRe)`, `__text(labelRe, value)`, `__fin()` (Review + Submit) and
`__submit()`, with a shadow-root walk to find the native `<dialog>`. Load it once with
`browser_run_code_unsafe` + `filename:`; it survives navigation. A loop that opens each job, calls
`__auto` and submits only when the review page holds nothing but contact + resume fields applied
13 Easy Apply jobs in ~25 min. `__fin` does not see "Invalid input" (plain text): if it returns
`review-failed`, read the dialog `innerText` (a numeric field wanted `2`, not "Microsoft Azure").
Before closing a half-filled dialog: `Dismiss` then `Discard`.

To save tool calls, batch bookkeeping into single `evaluate` calls (click a radio and
Review together; uncheck Follow and Submit together). This roughly halves the call
count with no loss of reliability (~25 applications in a row).

## Backlog

- Not swept yet (as of 2026-10-01): "Software Engineer", "Site Reliability Engineer",
  "Cloud Engineer" phrases for Madrid / Valencia / remote Spain.

## Beyond job search: people and profile

Not used by `/hunt` runs. Kept here so all LinkedIn mechanics live in one place.

**Company employees list:**
`https://www.linkedin.com/company/<slug>/people/?facetCurrentFunction=<id>&facetGeoRegion=<id>&facetSkillExplicit=<id>&keywords=<kw>`.
The real list is below the charts, under the heading "People you may know" (despite
the name, these are the filtered employees). Load more by clicking "Show more results"
in a JS loop:
`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Show more results')).click()`.
Collect profiles with `main[aria-label="Organization page for ..."] ul li a[href*="/in/"]`.

**"Is hiring" badge:** after loading the whole list, `img[alt*="is hiring"]` finds
everyone with the green "Hiring" frame in one `evaluate`, with no profile visits.

**Last activity of a person:** open `https://www.linkedin.com/in/<handle>/recent-activity/all/`
and read `document.querySelectorAll('span[class*="actor__sub-description"]')`; the
first spans hold relative times ("2w •", "3yr •"). No activity shows "Nothing to see
for now". A repost at the top also counts as the person's own activity.

**Who reposted a job post:**
1. Find the post with content search:
   `https://www.linkedin.com/search/results/content/?keywords=<company>%20hiring`.
   The company "Posts" tab (`company/<slug>/posts/`) does not render posts at all
   (empty `occludable-update-hint` blocks).
2. Get the post URN: JS-click "Open control menu for post by <Name>", then in
   `[role="menu"]` read the `href` of "Report post"; it contains
   `updateUrn=urn%3Ali%3Aactivity%3A<id>`.
3. Open `https://www.linkedin.com/feed/update/urn:li:activity:<id>/` and JS-click the
   button `aria-label="N reposts of X's post"`; a `[role="dialog"]` opens.
4. Extract names two ways and merge them: plain reposts match
   `/([A-ZÀ-ÿ][^\n]{2,60}?) reposted this/g` on `dialog.textContent`; quote reposts render
   as full post cards, so take names from `a[aria-label^="View: "]` or the
   `Follow <Name>` buttons. The total must equal the "N reposts" in the dialog header.

**Editing the candidate's own profile:**
- Intro/headline: `/in/<handle>/edit/intro/`. About:
  `/in/<handle>/edit/forms/summary/new/` (`/edit/about/` is a 404). A position:
  `/details/experience/edit/forms/<id>/` (the id comes from links on `/details/experience/`).
- The fields are tiptap contenteditables inside a frame, invisible to
  `document.querySelector` in `evaluate`. Use `browser_run_code_unsafe` with
  `page.getByRole('dialog')`. Multi-paragraph text: Ctrl+A, Delete, then
  `keyboard.insertText` per paragraph plus Enter twice. To replace one line: triple-click
  `getByText(...)`, then `insertText`.
- Month/year are native `<select>` elements (`selectOption({label})`). After Save, a
  redirect to an upsell / next-action page means the change was saved.

**Open to Work preferences** (they steer the recommended collection):
- Edit form: `https://www.linkedin.com/in/<handle>/opportunities/job-opportunities/edit/`.
- **Hard limits: 5 job titles, 5 on-site locations, 5 remote locations.** At the limit
  the "Add title" / "Add location" button is disabled ("You've reached the maximum").
  Removing an item is a decision for the user.
- Remove: JS-click `button[aria-label="Remove <item>"]` inside `[role="dialog"]`.
  `browser_click` on the pill times out ("visible, enabled and stable").
- Add: JS-click the enabled "Add title" / "Add location" button. An
  `input[role="combobox"]` with `aria-label="Add title"` (or `"Add location"`) gets
  focus. Type with `browser_type` and `slowly: true`, wait ~1.5 s, then JS-click the
  exact `[role="option"]`. For Madrid, prefer "Greater Madrid Metropolitan Area" over
  the city: it covers the suburbs where many jobs sit.
- Save: JS-click "Save". Success redirects to `…/job-opportunities/confirmation/`
  ("Job preferences saved"). LinkedIn also creates job alerts for the titles. Skip its
  "start a post" suggestion.
- The "Add title" / "Add location" buttons are not inside `[role="dialog"]`: find them on
  the page by `aria-label`. Typing "Software Support" and clicking the typeahead can add it
  as a title by mistake; check the pill list with `button[aria-label^="Remove "]` before Save.
- Profile intro (`/edit/intro/`): the city is a native `<select>` after the postal code
  (28045 offers Madrid / Greater Madrid Metropolitan Area); use `selectOption({label})`.

## Saved resumes (`/jobs/application-settings/?hideTitle=true`)

- The page lists 4 resumes and hides the rest behind "+N more resumes": count after expanding.
- Upload: `page.locator('input[type=file]').first().setInputFiles(path)` (one file per call,
  the input stays on the page). The newest upload is listed first.
- Delete: the "..." button of a row (`getByRole('button', {name: /Show options for/})`)
  opens a popover with Delete / Download. Delete acts at once, no confirmation. Playwright's
  text and visibility checks do not see the popover; after a click, reload and count again.
