"""SerpAPI (Google Scholar engine) wrapper for surfacing candidate academic problems.

Returns raw paper metadata only — turning an abstract into a concrete
``problem_statement`` is an LLM step, done downstream by the Gemini prompt in
``/flows/prompts/academic_problem_extraction.md`` once this node is wired into
the Langflow flow.
"""
from __future__ import annotations

import datetime
import os

from serpapi import GoogleSearch

from app.utils.negative_context import extract_negative_keywords


def _build_query(topic: str, domain_filters: list[str] | None, negative_context: str | None) -> str:
    query = topic
    if domain_filters:
        query += " " + " OR ".join(domain_filters)
    for keyword in extract_negative_keywords(negative_context):
        query += f' -"{keyword}"'
    return query


def search_academic_problems(
    topic: str,
    domain_filters: list[str] | None = None,
    negative_context: str | None = None,
    num_results: int = 10,
    years_back: int = 6,
    api_key: str | None = None,
) -> list[dict]:
    """Query Google Scholar via SerpAPI and return candidate academic problem sources."""
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        raise RuntimeError("SERPAPI_KEY is not set")

    params = {
        "engine": "google_scholar",
        "q": _build_query(topic, domain_filters, negative_context),
        "api_key": key,
        "num": min(num_results, 20),
        "as_ylo": datetime.date.today().year - years_back,
    }
    results = GoogleSearch(params).get_dict()

    papers = []
    for item in results.get("organic_results", [])[:num_results]:
        publication_info = item.get("publication_info", {})
        cited_by = item.get("inline_links", {}).get("cited_by", {})
        papers.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "abstract": item.get("snippet", ""),
                "authors_summary": publication_info.get("summary", ""),
                "citation_summary": f"{cited_by.get('total', 0)} citations" if cited_by else "0 citations",
                "cited_by_link": cited_by.get("link", ""),
            }
        )
    return papers
