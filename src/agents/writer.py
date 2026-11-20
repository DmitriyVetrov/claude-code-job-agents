"""The report writer agent (the report-writer role).

Read-only, no tools: it receives the evaluated jobs and returns finished markdown
text. The file is written to disk by the orchestrator, not by this agent.
"""
from __future__ import annotations

from agent_framework.anthropic import AnthropicClient

from config import CHAT_MODEL, load_prompt


def build_writer(client: AnthropicClient | None = None):
    client = client or AnthropicClient(model=CHAT_MODEL)
    return client.as_agent(
        name="report-writer",
        instructions=load_prompt("writer"),
    )
