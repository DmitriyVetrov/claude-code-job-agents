# Job Hunt — port to Microsoft Agent Framework (Python)

A port of the job-hunt project from Claude Code to [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/)
(MAF), with Anthropic (Claude) as the provider. The same three-role team —
**finder → matcher → writer** — but assembled as a standalone Python application.

> **Status: skeleton.** The scaffolding and the agent/orchestrator wiring are
> real (per the MAF docs), but most of the job sources are stubs with TODOs, and
> the code has not yet been run for real. This is a starting point, not a
> finished pipeline.

## Mapping to the Claude Code version

| Claude Code | MAF (this version) |
|---|---|
| `CLAUDE.md` (orchestrator) | `main.py` — sequential orchestration |
| `.claude/agents/job-finder.md` | `agents/finder.py` + `prompts/finder.md` |
| `.claude/agents/job-matcher.md` | `agents/matcher.py` + `prompts/matcher.md` |
| `.claude/agents/report-writer.md` | `agents/writer.py` + `prompts/writer.md` |
| Built-in WebFetch/WebSearch | `tools/sources.py` + hosted web search |
| Playwright MCP (LinkedIn) | not connected yet (MAF supports MCP — see TODO) |

The "CV = profile" principle is preserved: candidate-specific tuning comes from
`../docs/cv.txt`, and the prompts in `prompts/` define the roles' behavior.
The "only the orchestrator writes" principle is preserved too: the agents have no
write tools, and `main.py` is what saves the report to disk.

## Layout

```
src/
├── main.py              # orchestrator: CV → finder → matcher → writer → reports/
├── config.py            # paths, model, .env loading, reading prompts and the CV
├── requirements.txt
├── .env.example
├── agents/
│   ├── finder.py        # finder (the only one with tools)
│   ├── matcher.py       # matcher (read-only)
│   └── writer.py        # report writer (read-only)
├── tools/
│   └── sources.py       # function tools: RemoteOK, Remotive (ready);
│                        #   InfoJobs, Tecnoempleo (stubs)
└── prompts/
    ├── finder.md
    ├── matcher.md
    └── writer.md
```

## Installation

```bash
cd src
python -m venv .venv && source .venv/bin/activate
pip install --pre -r requirements.txt   # the MAF package is still pre-release
cp .env.example .env                     # then fill in ANTHROPIC_API_KEY
```

## Running it

```bash
cd src
python main.py
```

The orchestrator reads `../docs/cv.txt`, runs the chain, and saves the report to
`../reports/jobs-YYYY-MM-DD.md`.

## What's left to do (TODO)

- **Stub sources** in `tools/sources.py` (`fetch_infojobs`,
  `fetch_tecnoempleo`) — HTML scraping, following the pattern of the finished
  RemoteOK/Remotive ones. Add the rest from the Claude Code version
  (WeWorkRemotely RSS, LandingJobs, WeAreDevelopers, profesia.sk, djinni.co).
- **LinkedIn / talent.io** — connect via MCP (MAF: `client.get_mcp_tool(...)`
  for hosted, or `MCPStdioTool`/`MCPStreamableHTTPTool` for local; the existing
  Playwright MCP and the `../browser-data` session can be reused).
- **Structured exchange between agents** — right now the roles pass each other
  plain text; this could move to structured outputs (JSON schemas) for
  reliability.
- **Workflow** — replace the sequential `main.py` with a MAF Workflow graph
  (checkpointing, human-in-the-loop) if the need arises.
