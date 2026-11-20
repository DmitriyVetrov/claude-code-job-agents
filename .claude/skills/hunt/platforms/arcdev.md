# arc.dev

> Last verified: 2026-09-29 · Access: browser (logged in) · Apply: yes (Fast apply)
> Curated remote marketplace with full-time and freelance "Fast apply" roles; many are geo-blocked for Spain.

## Access

The logged-in session lives in the Playwright profile `browser-data/`. Three dashboards:

| Dashboard | What it is |
|---|---|
| `/dashboard/d/full-time-jobs/browse` | Curated "Arc Exclusive / Fast apply" permanent roles, ~14 at a time. Ends with a "Nothing catching your eye? Browse external global remote jobs" link when exhausted. |
| `/dashboard/d/freelance-jobs/browse` | Same Fast apply flow for contract roles, ~30 at a time; a finite list with no "load more". |
| `/dashboard/d/global-remote-jobs/browse` | External aggregator (4,000+ jobs). "Apply now" leaves Arc for LinkedIn or the company's ATS. A different, much larger effort; do not treat it like the two curated dashboards. |

## Search

- "Filters" → Role = **Developer** removes non-engineering postings. The filter persists
  across the full-time/freelance tab switch.
- Both tracks share the same dashboards; classify jobs by stack.

## Filters and traps

- **Check eligibility first.** Every job dialog has a "Location" field right under the
  title: "Remote anywhere", "Open to candidates in Spain", or "Not open to candidates in
  Spain" (with a "See all remote locations" link). `browser_find({text: "Location"})`
  right after opening a job avoids reading the description of blocked jobs.
- A large share is geo-blocked for Spain: India only, Brazil only, LATAM/NA only, US
  only, or visa-sponsored relocation allowlists (for example Chile, Canada, Mexico,
  Singapore). "Remote anywhere" is not the default.
- Typical hard domain mismatches seen: telephony/PBX, Supabase RLS security audits,
  Stripe Connect, OCPP/EV charging, Shopify/Magento builds, AppSec code review,
  streaming pipelines (RTMP/OBS), trading/quant, mobile-only (iOS/Android/Flutter/React
  Native), GIS/CesiumJS, Bitcoin Lightning, NetSuite, Sage X3.
- Fractional CTO / architect roles: skip unless asked.

## Job ID

The job slug or ID from the job dialog URL.

## Apply (Fast apply)

1. Click "Fast apply"; the form appears inline in the same dialog.
2. **"Relevant experience"** looks like a plain `<div data-testid="placeholder">`, with no
   contenteditable in the DOM until clicked. It is a lazily mounted Draft.js editor
   (`public-DraftEditor-content`). Click the placeholder first
   (`browser_find({text:"Add specific examples"})`), re-snapshot to find the newly mounted
   `textbox "relevantExperiencesDescription"`, then type a short, tailored blurb.
3. Full-time jobs: the experience field is optional, and one Submit click is enough.
4. Freelance jobs add "Expected rate for this job" (prefilled from the profile default,
   $20/hour) and "You're available for" (radio, defaults to the job's hours/week). The
   experience field is sometimes required (`*`), and Submit stays disabled until it is filled.
5. Submit sometimes times out on the first click ("waiting for element to be visible,
   enabled and stable"); a second click goes through.
6. Confirm with `browser_find({text: "Application sent"})`. Do not trust the click result.

## Backlog

- 2026-09-29: 7 applications sent from the two curated dashboards. The
  global-remote-jobs board (4,163 external listings) was not processed; it needs a
  per-job, per-ATS approach.
