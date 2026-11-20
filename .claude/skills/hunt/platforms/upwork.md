# Upwork

> Last verified: 2026-10-07 · Access: browser (logged in) · Apply: blocked (needs Connects)
> Freelance marketplace; typical .NET postings pay $20-40/h and draw 50+ proposals within a day.

## Access

- The logged-in session (Freelancer Basic plan) lives in the Playwright profile `browser-data/`.
  On 2026-10-23 it had expired (search redirected to `/ab/account-security/login`, not the
  Cloudflare page) while Djinni in the same profile was still logged in: re-login needed.
- **Connects:** the account still had 1 Connect on 2026-10-07. A proposal costs
  **14-19 Connects** (16 and 19 on .NET roles, 14-15 on fixed-price ones; the
  2026-10-02 run saw 24-27, so the price varies per job). Connects must be bought
  before any application. The job page prints both "Required Connects to submit a
  proposal: N" and "Available Connects: N", so read the cost per job rather than
  assuming one figure.
- **Account state (2026-10-08 profile review):** Basic plan gives **0 Connects/month**, so
  every proposal is a cash purchase. ID is verified but the **IDV Badge is not issued** (needs
  35 Connects, deadline ~2026-10-14) and the public profile shows "Unverified". **Tax profile
  (W-8BEN) is not submitted and there is no withdrawal method**, so earnings cannot be paid out
  yet — flag this before any apply run. Full audit: `reports/upwork-profile-review-2026-10-08.md`.
- Invites tab: `/nx/find-work/invites` (only $5 survey invitations on 2026-10-02).

## Search

`https://www.upwork.com/nx/search/jobs/?q=<query>&sort=recency&payment_verified=1&per_page=50`

| Track | Queries |
|---|---|
| swe | `.NET`, `C#`, `ASP.NET Core` |
| devops | `DevOps`, `Kubernetes`, `Terraform` |

## Extraction

- The DOM selectors for cards do not match. Split `document.body.innerText` on
  `\nPosted ` and take the links `a[href*="/jobs/"][href*="~"]` in the same order.
  Confirmed working 2026-10-07: `innerText.split('\nPosted ').slice(1)` lines up
  one-to-one with the links, and each part carries the title, client stats, rate,
  proposal count and the first ~900 chars of the description — enough to triage
  without opening the job. Pull the id with `href.match(/~(\w+)/)`.
- Highlight spans pollute titles and URLs. Open jobs by
  `https://www.upwork.com/jobs/~<id>`.
- The job page `innerText` contains "Required Connects to submit a proposal: N",
  "Available Connects", client stats (hires, hire rate, rating, payment verified) and
  **"Location: …"** under Preferred qualifications.

## Filters and traps

- **First navigation hits a Cloudflare challenge** ("Just a moment...", HTTP 403).
  It clears itself: `browser_wait_for` about 8 seconds and the page title becomes
  "Search Freelance Jobs on Upwork". Don't retry the navigation, just wait
  (2026-10-07).
- **The card's "Location" is the CLIENT's country, not a requirement.** It is the
  single biggest source of false filtering here. The job page's own geo line is
  separate: it prints "Worldwide" when there is no restriction. Every job checked on
  2026-10-07 said Worldwide, including clients in Ukraine, Azerbaijan, Vietnam and
  Oman.
- "Location: …" under **Preferred qualifications** on the job page *is* a hard geo
  filter (for example India/Philippines only); Spain is allowed in some.
- **Most real geo restrictions are buried in the description, not in a field.**
  "US Only", "we are seeking a U.S.-based developer", "must be based in the U.S. or
  Canada" appeared in 6 of 85 postings on 2026-10-07 with no geo field set. Grep the
  description text for `US-based`, `U.S.-based`, `US Only`, `Native English`.
- A recurring posting family: agencies hiring a **"technical representative"** to sit
  in client calls — "this is a non-coding role", US-based. Four of these on
  2026-10-07, often at an implausible $70-120/h from a $0-spent client. Not dev work.
- Some postings require EU/UK citizenship; a permanent residence does not qualify.
- Language bars are common and are hard blockers: "Native English speaker",
  "C2 Level or Native", "near-native English", and on Spain-based clients
  "professional-level Spanish or higher" (candidate is English B2 / Spanish B1).
- Check competition: proposals count and "interviewing" count; a new client with no
  history is a risk. On the recency-sorted .NET searches most postings sit at
  "Proposals: 50+"; the 5-15 proposal ones are where the odds are. The job page also
  gives "Interviewing: N" and "Invites sent: N" — 15 interviewing plus 19 invites
  means the shortlist is already built.
- Client quality signals worth reading off the job page: total spent, hire rate,
  rating and **average hourly rate paid**. A 5.0 / 92%-hire-rate client whose average
  paid rate is $14/h will not pay the target rate.
- Fixed-price budgets are often placeholders ($5, $10, $50, $100 on long-term senior
  roles). Treat an absurd budget on an otherwise serious posting as unknown, not as
  the offer — but a $5 budget with a $5-spend client is just noise.
- Rates: preferences.md.

## Job ID

`~<id>` from the job URL.

## Apply

Not until Connects are bought. In apply mode, stop and tell the user how many
Connects the shortlisted proposals need.
