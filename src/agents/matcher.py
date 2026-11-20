"""The job-fit matcher agent (the job-matcher role).

Read-only, no tools: it only reasons over the CV and job list it is given and
assigns MATCH / WEAK / NO_MATCH verdicts.
"""
from __future__ import annotations

from agent_framework.anthropic import AnthropicClient

from config import CHAT_MODEL, load_prompt


def build_matcher(client: AnthropicClient | None = None):
    client = client or AnthropicClient(model=CHAT_MODEL)
    return client.as_agent(
        name="job-matcher",
        instructions=load_prompt("matcher"),
        # No tools passed — the matcher neither searches nor writes.
    )
