"""Function tools for collecting jobs from open sources.

Each tool is a plain async function that the finder agent calls at its own
discretion. We start with open JSON/RSS APIs (cheap, no login); HTML scraping of
the regional boards and the browser-gated sources (LinkedIn) are stubs with
TODOs. The Annotated type hints describe the parameters for the model.
"""
from __future__ import annotations

import json
from typing import Annotated

import httpx

_UA = {"User-Agent": "Mozilla/5.0 (compatible; job-hunt-maf/0.1)"}
_TIMEOUT = httpx.Timeout(20.0)


async def fetch_remoteok(
    keywords: Annotated[
        str, "Comma-separated stack keywords, for example '.net,c#,backend'"
    ],
) -> str:
    """Pull jobs from RemoteOK's public JSON feed (https://remoteok.com/api).

    Returns a JSON string with a list of jobs. Filters roughly on keywords in the
    title/tags/description — the fit evaluation is done by the matcher agent, not
    by this tool.
    """
    terms = [t.strip().lower() for t in keywords.split(",") if t.strip()]
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_UA) as client:
        resp = await client.get("https://remoteok.com/api")
        resp.raise_for_status()
        data = resp.json()

    jobs = []
    for item in data:
        # The feed's first element is metadata, not a job.
        if not isinstance(item, dict) or "position" not in item:
            continue
        haystack = " ".join(
            [
                str(item.get("position", "")),
                str(item.get("description", "")),
                " ".join(item.get("tags", []) or []),
            ]
        ).lower()
        if terms and not any(t in haystack for t in terms):
            continue
        jobs.append(
            {
                "source": "RemoteOK",
                "title": item.get("position"),
                "company": item.get("company"),
                "location": item.get("location") or "remote",
                "url": item.get("url"),
                "tags": item.get("tags"),
                "description": (item.get("description") or "")[:1200],
            }
        )
    return json.dumps(jobs[:50], ensure_ascii=False)


async def fetch_remotive(
    search: Annotated[str, "Search query, for example '.net' or 'c#'"],
) -> str:
    """Pull jobs from Remotive's open API (https://remotive.com/api/remote-jobs).

    Returns a JSON string (source, title, company, location, url, description).
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_UA) as client:
        resp = await client.get(
            "https://remotive.com/api/remote-jobs", params={"search": search}
        )
        resp.raise_for_status()
        data = resp.json()

    jobs = [
        {
            "source": "Remotive",
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("candidate_required_location") or "remote",
            "url": j.get("url"),
            "description": (j.get("description") or "")[:1200],
        }
        for j in data.get("jobs", [])
    ]
    return json.dumps(jobs[:50], ensure_ascii=False)


# --- Stubs: implement following the pattern above (HTTP GET + HTML/RSS parsing) --
# These are the sources where the Claude Code version used WebFetch: they have no
# convenient JSON API and need HTML scraping (httpx + selectolax/bs4).


async def fetch_infojobs(
    query: Annotated[str, "Stack, for example '.NET' / 'C#'"],
    province: Annotated[str, "Spanish province, for example 'Valencia'"] = "",
) -> str:
    """TODO: HTML scraping of infojobs.net (Spain's largest board). Empty for now."""
    # TODO: httpx.get the search page (query + provincia, and teletrabajo
    #       separately), parse the HTML, collect
    #       title/company/location/url/description.
    return json.dumps([], ensure_ascii=False)


async def fetch_tecnoempleo(
    query: Annotated[str, "Stack, for example '.NET' / 'C#'"],
) -> str:
    """TODO: HTML scraping of tecnoempleo.com (Spanish IT board). Empty for now."""
    return json.dumps([], ensure_ascii=False)
