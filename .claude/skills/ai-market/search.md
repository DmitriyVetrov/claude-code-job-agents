# AI market search

> Created 2026-10-22 · none of the phrases below is swept yet: record the card counts the first
> time each one runs, as the `/hunt` playbooks do.

The goal is a **representative sample of what employers want**, not only jobs the
candidate can get. So the phrases cover the whole AI-engineering spectrum, and the
regions include markets that are not reachable today (they show where the market goes).

## Regions

| Region | Why | Reachable for the candidate (Spain permanent resident, not EU citizen) |
|---|---|---|
| Spain | home market, international companies | yes |
| EU remote | main reachable remote market | yes, if the employer hires Spanish residents (EOR / B2B) |
| Netherlands | strong AI startup scene | relocation with Highly Skilled Migrant sponsorship (recognised sponsor) |
| United Kingdom | biggest AI job market in Europe | not as an employee without a Skilled Worker visa; yes as a remote B2B contractor |
| Ireland | | blocked without a Critical Skills permit; research only |
| US / global remote | where titles and stacks are defined first | mostly research only; contractor roles sometimes |

## Phrases

Use each platform's quoting rules (LinkedIn: always URL-encoded quotes, see its playbook).

| Group | Phrases |
|---|---|
| core | "AI Engineer", "Applied AI Engineer", "LLM Engineer", "GenAI Engineer", "Generative AI Engineer", "AI Application Engineer", "AI Software Engineer" |
| agents | "Agentic AI", "AI Agent Engineer", "AI Agents Developer", "Agent Engineer" |
| automation | "AI Automation Engineer", "AI Automation Specialist", "Automation Engineer" n8n, "AI Workflow" |
| solutions | "AI Solutions Engineer", "Forward Deployed Engineer", "AI Solutions Architect", "AI Implementation" |
| integration | "Backend Engineer" AI, "Software Engineer" LLM, "AI Integration", "MCP" |
| dotnet | ".NET" OpenAI, "C#" LLM, ".NET" "Azure OpenAI", "Semantic Kernel", ".NET" AI |
| entry doors | "AI Evaluation", "LLM Evaluation", "AI QA", "Prompt Engineer", "Junior AI Engineer" |

The `dotnet` group matters most for `hunt_candidate` finds; the `core` and `agents`
groups give the bulk of the sample.

## Platforms

| Platform | How | Notes |
|---|---|---|
| linkedin | guest endpoint (curl, foreground) or the logged-in browser | `location=` Spain, European Union, Netherlands, United Kingdom, Ireland, United States. Window `week` by default (`f_TPR=r604800`). Description: guest `jobPosting/<id>`. |
| remote-boards | open HTTP, may be delegated to `job-finder` | RemoteOK `?tag=ai`, `?tag=llm`, `?tag=machine-learning`; Remotive `?search=AI%20engineer`, `?search=LLM`; We Work Remotely programming RSS filtered by AI/LLM/agent in the title. |
| djinni | browser (logged in) | Ukrainian market, a lot of remote outsourcing AI work. `primary_keyword=ML%20AI` (verified 2026-10-23) plus `all_keywords=<phrase>` with `region=eu` / `worldwide`; `keywords=` is ignored. `country=ESP` gives 0-1 AI cards. |
| upwork | browser | **Demand signal for freelance**: what clients pay for (n8n + LLM automations, RAG chatbots, agents). Queries: `AI agent`, `LLM`, `RAG`, `n8n AI`, `MCP`. Record budget / hourly range in `salary`. |

Wellfound is the obvious missing source for AI startups: there is no session and no playbook yet (see `/hunt` **Unavailable sources**).

## Caps per run

- At most **60 new postings per platform per run** with full descriptions (a digest
  needs breadth over time, not one huge pull).
- Spread a run over the groups: no more than ~15 postings from one phrase.
- LinkedIn: follow the playbook's pacing; stop on HTTP 429 and say so.
