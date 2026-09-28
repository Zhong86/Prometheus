"""Tavily advanced-search wrapper for surfacing real-world user friction (micro pain points).

Searches review/forum sites where users complain about existing tools, so the
``synthesize`` node has raw material to pair against academic problems.
"""
from __future__ import annotations

import os

from tavily import TavilyClient

from app.utils.negative_context import extract_negative_keywords

PAIN_SITES = ["capterra.com", "g2.com", "reddit.com", "trustpilot.com"]
PAIN_PHRASES = [
    '"doesn\'t work"',
    '"so clunky"',
    '"wish it could"',
    '"biggest frustration"',
    "clunky",
    "workaround",
]


def _build_queries(topic: str, negative_keywords: list[str] | None) -> list[str]:
    exclusions = "".join(f' -"{kw}"' for kw in (negative_keywords or [])[:5])
    phrase_clause = " OR ".join(PAIN_PHRASES)
    return [f'site:{site} "{topic}" ({phrase_clause}){exclusions}' for site in PAIN_SITES]


def search_public_friction(
    topic: str,
    negative_context: str | None = None,
    max_results_per_site: int = 4,
    api_key: str | None = None,
) -> list[dict]:
    """Search Capterra, G2, Reddit, and Trustpilot for raw complaint/review quotes."""
    key = api_key or os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set")

    client = TavilyClient(api_key=key)
    negative_keywords = extract_negative_keywords(negative_context)

    complaints: list[dict] = []
    for query in _build_queries(topic, negative_keywords):
        response = client.search(
            query=query,
            search_depth="advanced",
            include_raw_content=True,
            max_results=max_results_per_site,
        )
        for result in response.get("results", []):
            complaints.append(
                {
                    "source": result.get("url", ""),
                    "title": result.get("title", ""),
                    "quote": result.get("content", ""),
                    "raw_content": result.get("raw_content", ""),
                    "score": result.get("score", 0.0),
                }
            )
    return complaints
