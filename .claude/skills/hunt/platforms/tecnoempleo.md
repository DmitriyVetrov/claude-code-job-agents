# Tecnoempleo

> Last verified: 2026-10-29 · Access: browser (logged in) · Apply: yes (one-shot URL)
> Spanish IT-only board (tecnoempleo.com); the most tech-focused source in Spain.

## Access

- The candidate's account is logged in through the Playwright profile `browser-data/`.
  If the session expired, the **"Login con Google"** button signs in without a password.
  An expired session shows up as a redirect to `demanda-trabajo-informatica.php?finsesion=1`
  ("se ha cerrado automáticamente tu sesión"); expect it after a few weeks without a run.
- The first request may show a Cloudflare "Just a moment..." page (HTTP 403); wait ~8 s
  and it passes on its own.
- Candidate area: applications `/profesionales/segui.php`, notifications
  `/profesionales/notificaciones.php`, messages `/profesionales/mensajesp.php`.

## Search

`https://www.tecnoempleo.com/ofertas-trabajo/?te=<term>&pagina=<N>`

| Track | Terms |
|---|---|
| swe | `.net`, `c#`, `sql server`, `azure`, `react` |
| devops (Junior SRE) | `sre` |
| offer-max | `soporte`, `qa`, `tester`, `junior`, `helpdesk` |

- Results are sorted newest first, so stop paging a term once a whole page is older
  than the 30-day freshness cutoff. Last 24 h only: `?ult_24h=1` (the "Hoy" link).
- Fetching the search pages with `fetch()` inside the logged-in tab and parsing them
  with `DOMParser` is much faster than navigating (keep ~0.7 s between requests).
- `?te=` matches the whole posting text, so `sre`, `soporte` and `azure` return hundreds
  of unrelated cards (2026-10-29: `soporte` 349 in 30 days). Pre-filter by title and by
  location before opening descriptions.

- `?te=` is **free-text** search: it does not filter by company and is reliable for
  company names only when the brand is distinctive.
- The result count is in the heading "N Ofertas Trabajo de <term>" (the old
  `trackSiteSearch` marker is gone as of 2026-10-29).
- The `.net` search had 79 listings on 2026-10-29 (53 of them within 30 days).

## Extraction

- The job URL contains `rf-<CODE>`. That code is the job ID and the apply key.
- Search cards: `div.p-3.border.rounded.mb-3.bg-white`. Inside: the first `a[href*="/rf-"]`
  is the title; card lines are title, company, "Location (Modalidad) - dd/mm/yyyy",
  then the salary if shown ("54.000€ - 72.000€ b/a").
- Job page: description in `div.fs--16.text-gray-800`; facts (Ubicación, "Imprescindible
  Residir", Funciones, Jornada, Experiencia, Tipo contrato) in `li.list-group-item`.
- Location "Madrid (Presencial)" = full on-site; "(Híbrido)" rarely states the days.
- Some job pages show "tu CV es un NN% Compatible con esta Oferta". It is a useful
  relevance signal, but it renders inconsistently (often missing, and loaded async, so
  raw `fetch()` misses it). Read the description too.

## Filters and traps

- **Reposts:** the same role from the same company appears under different `rf-` codes
  (Michael Page "Arquitecto .NET" ×3, Plexus "Senior .NET Developers" ×2, UST
  "Full Stack .NET/React" ×2). Dedupe by company + title against both `segui.php` and
  the current batch.
- **"(Oferta externa)":** Tecnoempleo logs the CV send (visible in `segui.php`) and then
  redirects to the employer's own ATS (RippleHire, Workday, …). Treat the Tecnoempleo-
  side log as the completed action; do not chase the external form.
- Social You postings: a recruiting intermediary that collects CVs; low value.

## Rate limits

**Daily application cap ("vinculaciones").** Once it is hit, every apply attempt
redirects to `candidato_restringido.php?tp=spm` with a 24 h cooldown. On 2026-09-29 the
cap was hit after **31 applications** in one session. Budget runs accordingly.

## Job ID

`rf-<CODE>` from the job URL.

## Already applied

`/profesionales/segui.php`. Count only the `leeroff5.php?refer=<CODE>` links: each card
also carries an "Oferta similar: ..." link with an `rf-` code that is a suggestion, NOT an
application. Paginate with `segui.php?carpeta=&estado=&pagina=<N>&ordenar=fechadesc`.

## Apply

1. Navigate directly to
   `https://www.tecnoempleo.com/enviar.php?nue_fin=&refer=<CODE>&TK=`.
   For most listings this submits in one request and lands on `insercion=valida`. There
   is no need to open the job page or click "Inscribirme a Oferta".
2. If an intermediate form appears instead:
   - only an optional cover-letter dropdown or a "condiciones particulares" acceptance:
     finish with `document.getElementById('btn_vinculacion').click()` via `browser_evaluate`;
   - **mandatory screening questions** (yes/no availability, salary, free-text
     experience): answer per preferences.md. If a factual question would need a false
     answer (for example "available 3 days/week on-site in X?"), skip the job.
3. Success: `insercion=valida` in the URL, and the job appears in `segui.php`.

## Backlog

None. The 2026-09-29 backlog was superseded by the 30-day sweep of 2026-10-29.
