# Empléate (SEPE)

> Last verified: 2026-07-09 · Access: open HTTP (internal Solr API; browser for the UI) · Apply: no
> Spain's public aggregator (empleate.gob.es): pulls jobs from regional job centres, Tecnoempleo and EURES.

## Access

- An Angular SPA with hash routing. The UI search is
  `https://empleate.gob.es/#/trabajo?search=<kw>&pag=0&…`.
- **The internal API is better than clicking the UI** (see Extraction).

## Search

UI URL parameters (verified 2026-07-08):

- `search=*` for everything; `search=.net` for a keyword (matches mostly the title, very precise)
- `pag=0`: page, zero-based
- `provincia=`: Valencia 46, Madrid 28, Barcelona 08, Sevilla 41, Vizcaya 48, Guipúzcoa 20,
  Zaragoza 50, Málaga 29, Valladolid 47
- `categoria=17`: Informática y telecomunicaciones; `categoria=18`: Ingeniería/calidad/ciencias
- `subcategoria=17001` (Analistas y programadores) does **not** narrow anything; it gives
  the same results as `categoria=17`
- `modalidad=true` ("Admite teletrabajo") is a **trap**: almost empty (16 IT jobs in all
  of Spain), because job centres do not fill the flag. Find remote jobs by keyword or
  title (híbrido / remoto / 100% en remoto) instead.
- `pais=724`: España

| Track | Keywords |
|---|---|
| swe | `.net`, `c#` |
| devops | `azure`, `kubernetes`, `devops` |

Volumes seen: `.net` Valencia 56, `.net` all of Spain 392, `azure` Spain 324,
`categoria=17` + Valencia 105 (noisy).

## Extraction

Solr endpoint: `GET https://empleate.gob.es/empleate/open/offersearch/selectBuscador`

- `q=<kw>`, `fq=categoria:"17"`, `fq=(speStateId:1 OR speStateId:4) AND checkVisible:1`
  (visible/active only), `start=<offset>&rows=<n>`, `wt=json`. Drop `json.wrf=…` to get
  clean JSON instead of JSONP.
- **`rows` is capped around 200** by the backend, and a large `start` truncates further.
  Paginate with `rows=50` in steps of 50 from `start=0` to reach every `numFound`.
- It is same-origin, so the easiest route is `fetch()` inside Playwright
  `browser_evaluate`, accumulating into `window.__jobs`. Dedupe by `externalId`.
- Document fields: `titulo`, `contenido` (the full description), `contacto` / `creador`
  (company), `ciudadF` / `provinciaF` / `paisF`, `url` (link to the source portal),
  `origen` / `entitytype` (TECNO_EMPLEO / EURES / LABORA), `modality`, `tipoContrato`,
  `fechaCreacionFormateada`.
- `browser_evaluate` with `filename=…` saves the **result** as a JSON string (quoted,
  with `\n`) in `.playwright-mcp/<file>`. Decode it with `json.load` before writing a report.

## Filters and traps

- A keyword search is far more precise than a category filter: `categoria=17` is full of
  helpdesk / soporte / RRHH / industrial roles.
- Source portals: TECNO_EMPLEO (the most tech), LABORA (Valencia's job centre, often
  junior / helpdesk / FP), EURES (EU jobs for relocation). The "Por portal de origen"
  filter can keep TECNO_EMPLEO only.
- The UI allows up to 100 items per page.
- 2026-07-09: `q=ingles&categoria=17` returned 635 (615 unique); after classification:
  25 strong (.NET), 151 moderate, 79 weak, 360 dropped.

## Job ID

`externalId`.
