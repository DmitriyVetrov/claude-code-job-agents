"""The job finder agent (the job-finder role).

The only one of the three agents that has tools: function tools for the open
sources plus Anthropic's hosted web search (the same server-side web_search that
Claude Code uses).
"""
from __future__ import annotations

from agent_framework.anthropic import AnthropicClient

from config import CHAT_MODEL, load_prompt
from tools import OPEN_SOURCE_TOOLS


def build_finder(client: AnthropicClient | None = None):
    """Create the finder agent: open sources + hosted web search."""
    client = client or AnthropicClient(model=CHAT_MODEL)
    tools = [*OPEN_SOURCE_TOOLS, client.get_web_search_tool()]
    return client.as_agent(
        name="job-finder",
        instructions=load_prompt("finder"),
        tools=tools,
    )
