"""Tavily wrapper for finding existing products/competitors that solve a synthesized problem."""
from __future__ import annotations

import os

from tavily import TavilyClient


def search_competitors(
    problem_statement: str,
    max_results: int = 8,
    api_key: str | None = None,
) -> list[dict]:
    """Search for existing SaaS/products addressing the synthesized problem statement."""
    key = api_key or os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set")

    client = TavilyClient(api_key=key)
    query = f'"{problem_statement}" software product OR SaaS OR app pricing reviews'
    response = client.search(
        query=query,
        search_depth="advanced",
        include_raw_content=True,
        max_results=max_results,
    )
    return [
        {
            "source": result.get("url", ""),
            "title": result.get("title", ""),
            "content": result.get("content", ""),
            "raw_content": result.get("raw_content", ""),
            "score": result.get("score", 0.0),
        }
        for result in response.get("results", [])
    ]
