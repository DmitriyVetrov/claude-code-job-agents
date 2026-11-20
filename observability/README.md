# Observability: Claude Code runs in Grafana

Local only. Prompts are stored in plain text, so everything binds to `127.0.0.1`.

```
claude ──OTLP/http──► 127.0.0.1:14318 ──► collector ──► Tempo (traces)
                                                   ├──► Loki (events/logs)
                                                   └──► Prometheus (metrics)
                                                          ▼
                                              Grafana http://localhost:3001
```

## Start / stop
```bash
docker compose -f observability/docker-compose.yml up -d     # restart: unless-stopped
docker compose -f observability/docker-compose.yml down       # data stays in volume observability_lgtm-data
```
This stack is separate from `~/git/ibkr-ai-trader`'s collector (ports 3000/4317/4318). That
collector deletes the `prompt` attribute.

## Claude Code side
The variables live in `~/.claude/settings.json` → `"env"`. Project `.claude/settings.json`
ignores OTel exporter variables by design. They apply to **every** Claude Code session
on this machine: interactive, `claude -p` from `tg_bot.py`, remote-control. A session
picks them up only when it starts.

| Variable | Value | Why |
|---|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY` | `1` | master switch |
| `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` | `1` | traces (beta) |
| `OTEL_{METRICS,LOGS,TRACES}_EXPORTER` | `otlp` | all three signals |
| `OTEL_EXPORTER_OTLP_PROTOCOL` / `_ENDPOINT` | `http/protobuf` / `http://127.0.0.1:14318` | grpc needs Claude Code ≥ 2.1.323 |
| `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` | `cumulative` | Prometheus drops the default `delta` |
| `OTEL_METRIC_EXPORT_INTERVAL` | `10000` | metrics from the last <10 s before exit may be lost |
| `OTEL_LOGS_EXPORT_INTERVAL`, `OTEL_TRACES_EXPORT_INTERVAL` | `1000` | short `-p` runs |
| `OTEL_LOG_USER_PROMPTS` | `1` | prompt text (assistant text also follows it unless `OTEL_LOG_ASSISTANT_RESPONSES` is set) |

Not enabled yet. Turn these on to see *which* files, commands and scripts a run touches:
- `OTEL_LOG_TOOL_DETAILS=1`: tool arguments, Bash commands, file paths, MCP tool names.
- `OTEL_LOG_TOOL_CONTENT=1`: tool output inside trace spans.
- `OTEL_LOG_RAW_API_BODIES=1`: full API request/response bodies, including the whole conversation and the system prompt. Very large.

Backup of settings before the change: `~/.claude/settings.json.bak-otel`.

## Where to look (Grafana → Explore)
- **Tempo** → Search, `{resource.service.name="claude-code"}`. One trace = one prompt:
  `claude_code.interaction` → `llm_request` / `tool` → `tool.blocked_on_user`, `tool.execution`.
  Subagents (job-finder, job-matcher, …) nest under the Agent tool's `tool` span.
- **Loki**: `{service_name="claude-code"}`. Filter with `| event_name="user_prompt"` (or
  `api_request`, `tool_result`, `tool_decision`, `subagent_completed`). Every record has
  `trace_id`, `span_id`, `prompt_id`, `session_id`.
- **Prometheus**: `claude_code_cost_usage_USD_total`, `claude_code_token_usage_tokens_total`
  (by `model`, `agent_name`), `claude_code_session_count_total`, `claude_code_active_time_seconds_total`.

Tempo's search index lags ~30 s behind; lookup by trace ID works immediately.
