"""Job-collection tools. OPEN_SOURCE_TOOLS is passed to the finder agent."""
from .sources import (
    fetch_infojobs,
    fetch_remoteok,
    fetch_remotive,
    fetch_tecnoempleo,
)

# The function tools the finder receives. Hosted web search is added separately
# in build_finder() (it is bound to the client, not to the module).
OPEN_SOURCE_TOOLS = [
    fetch_remoteok,
    fetch_remotive,
    fetch_infojobs,
    fetch_tecnoempleo,
]

__all__ = [
    "OPEN_SOURCE_TOOLS",
    "fetch_remoteok",
    "fetch_remotive",
    "fetch_infojobs",
    "fetch_tecnoempleo",
]
