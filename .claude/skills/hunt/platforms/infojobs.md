# InfoJobs

> Last verified: 2026-10-29 · Access: browser (logged in for apply; guest for search) · Apply: yes
> Spain's largest job board (infojobs.net); descriptions are mostly in Spanish.

## Access

- WebFetch is **blocked** (HTTP 456) for almost every page. Use Playwright, or plain
  HTTP with a warmed-up session (see Extraction).
- Applying needs the candidate's account. When the session has expired InfoJobs asks
  for the password: the user enters it themselves. Never store it.
- There is no messages section; employer replies arrive by email.

## Search

- Keyword search: `https://www.infojobs.net/jobsearch/search-results/list.xhtml?keyword=<kw>&sinceDate=_24_HOURS&sortBy=PUBLICATION_DATE&page=N`
  (`sinceDate=_7_DAYS` for a gap; add `&provinceIds=<id>` for a province). The old
  `/webapp/offers/search?keyword=` returns HTTP 456 since 2026-10-28.
- From the logged-in browser (in-page `fetch`, `credentials: 'include'`) 20 queries × up to 3
  pages passed with no captcha (2026-10-29). Plain HTTP without the browser gets a captcha stub
  after ~4 searches: run the most valuable keywords first in that fallback.
- Province harvest:
  `https://www.infojobs.net/jobsearch/search-results/list.xhtml?provinceIds=<id>&sortBy=PUBLICATION_DATE&page=<N>`
  - **InfoJobs uses its own IDs, not INE codes:** Valencia/València `49`, Madrid `33`, Alicante `4`,
    Santa Cruz de Tenerife `46`. More IDs are in `d["aggregation"]["province"]`.
  - IT category "Informática y telecomunicaciones": `categoryIds=150`.

| Track | Keywords |
|---|---|
| swe | `.net`, `c#`, `sql`, `backend`, `azure`, `soporte aplicaciones .net` |
| devops (Junior SRE only, since 2026-10-22) | `sre`, `site reliability` |
| offer-max (since 2026-10-22) | `tester junior`, `soporte técnico`, `helpdesk`, `programador junior`; provinces Madrid, Valencia, Alicante |

## Extraction

- The data sits in `window.__INITIAL_PROPS__ = JSON.parse("...")`. Cut out the JS
  string literal and parse twice (`json.loads(literal)` gives the JSON text, then
  `json.loads` again).
- `d["offers"]` has full fields: `title`, `description`, `companyName`, `city`, `link`,
  `contractType`, `teleworking`, `publishedAt`. `d["navigation"]["totalPages"]`;
  22 offers per page.
- Without browser-like headers and cookies the server returns a ~29 KB stub without
  `__INITIAL_PROPS__`. Fix it by warming the session (GET `https://www.infojobs.net/`
  first, then search with a `Referer`), or use Playwright.
- 2026-09-26: the whole Valencia province (3,963 jobs, 199 pages) downloaded through
  Playwright in about 10 minutes without errors.

When the question is "do these companies have openings?", download the whole province
first and match company names afterwards. It is far cheaper than searching company by
company (see the matching rules in `industrial-parks.md`).

## Filters and traps

- Many listings repeat the same role under a different requisition; dedupe by
  company + title.
- Screening questionnaires can be detailed (RabbitMQ, Redis, testing, VB.NET, Crystal
  Reports, BizTalk). Answer honestly per preferences.md. If the core requirement is a
  whole technology with zero experience (BizTalk), skip.
- **Option matching:** a keyword-based answer picker once chose the *worst* option
  ("No conozco SQL Server" instead of "He programado SQL Server") and once claimed
  English "C1 o superior". Read every option. If the wording is ambiguous, flag the job
  for manual review, never default.

## Rate limits

No daily cap seen: 58 applications in one run on 2026-09-29.

## Job ID

The offer ID from the link: `…/of-i<id>`.

## Already applied

The candidate area of the logged-in account (applications list).

## Apply

- Apply from the job page with the account's CV, then answer the screening questions
  from the CV (preferences.md for languages, salary, visa).
- Confirm by the success page and the applications list.
- (2026-10-26) The short link `https://www.infojobs.net/of-i<id>` returns 404. Use a link
  with any city and slug, e.g. `https://www.infojobs.net/madrid/oferta/of-i<id>`. The
  apply form is at `/candidate/application/index.xhtml?id_oferta=<id without "of-i">`.
  On success you land on `search-results/list.xhtml?...&application=true` with the text
  "Te has inscrito correctamente en la oferta '<title>'".
- **One stored CV per account.** The form pre-attaches it. The file field appears only
  after "Eliminar CV adjunto", which opens a confirm dialog and deletes the CV from the
  account; then use "Seleccionar archivo". Check which city version is attached for
  every job, because the Madrid and Valencia PDFs show the same name and size. "Crear
  una carta" is pre-selected with an empty box: pick "No incluir carta" or write a note.
- Some employers show a data-protection "Acepto" pop-up first. The optional
  "Seleccionar opción export cv" (add the CV to the employer's database): leave it at No.
- **Swapping the stored CV per city** (2026-10-29): on any apply form click
  `button:has(span:text("Eliminar CV adjunto"))` (the span itself is visually hidden), accept the
  confirm "¿Quieres eliminar tu CV adjunto de InfoJobs?" (a `page.once('dialog', d => d.accept())`
  registered before the click handles it), then `setInputFiles` on the `input[type=file]` that
  appears. The Madrid and Valencia PDFs both show as ~71.9 KB: trust the order of operations, not
  the size. Swap back to the Madrid PDF after the last Valencia job.
  If the hidden-span click leaves the confirm open, accept it with `browser_handle_dialog`.
  `setInputFiles` on the input may silently do nothing: click "Seleccionar archivo" via
  `evaluate(b=>b.click())` and answer the file chooser with `browser_file_upload`; the
  upload persists to the account without submitting the application.
- **Stored-CV guard:** the account keeps one stored CV that other searches may replace. Before EVERY
  application read the file name under "CV adjunto" and swap in the right PDF from `docs/cv/<city>/`
  if it differs.
- Questionnaire text: read `document.body.innerText` between `\n1. ` and `CV adjunto`; radios are
  `preg_<n>` with labels, open questions `textarea-kq-<n>`. Some essays demand real projects in a
  stack the CV lacks (Access/VBA): list those for the user.
- Login now needs the password **and** an emailed device code ("Verifica tu
  identidad"), so unattended runs cannot log in again. The user has to do it at the
  laptop.

## Backlog

As of 2026-09-29:
- `.net` search: ~25 plausible jobs were triaged but not applied to (Avanade Jr Getafe,
  PHIOS Valencia, Métrica ×2, Cibernos ×2, WTW, IRIUM, ParkHelp, Etalentum, CIVIR, AARON
  (Dynamics integrations), TRAGSA, GESEIN, CTI, MNprogram, Aqualia, and others; full list
  in `reports/jobs-2026-09-29-infojobs-applications.md`).
- Not run: `C#`, `Azure`, `Kubernetes/DevOps`, `SQL`, `Backend`.
- Expected replies as of 2026-10-02: ALTIA, HISPATEC, Saal Digital (CV read).
