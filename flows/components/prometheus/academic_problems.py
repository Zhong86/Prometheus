"""Langflow node: academic_problems.

Wraps SerpAPI's google_scholar engine to surface candidate unsolved academic
problems for a topic. Wire the `papers` output into a Prompt + Google
Generative AI Model pair (see /flows/prompts/academic_problem_extraction.md)
to turn each abstract into a concrete `problem_statement`.

Self-contained on purpose: Langflow loads each component file through its own
bundle-module mechanism rather than a normal package import, so reaching
across to backend/app/tools/* via a sys.path trick doesn't reliably work at
runtime (fails with "ModuleNotFoundError: No module named 'app'"). The same
search logic also lives in backend/app/tools/academic_problems.py for the
FastAPI side; keep both in sync if the query-building logic changes.
"""
from __future__ import annotations

import datetime
import os

from serpapi import GoogleSearch

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output, SecretStrInput
from lfx.schema import Data


def _extract_negative_keywords(negative_context: str | None, limit: int = 5) -> list[str]:
    if not negative_context:
        return []
    keywords: list[str] = []
    for line in negative_context.splitlines():
        phrase = line.strip().lstrip("-").strip()
        if not phrase or phrase.lower().startswith("none yet"):
            continue
        keywords.append(phrase.split(":")[0][:60])
        if len(keywords) >= limit:
            break
    return keywords


def _build_query(topic: str, domain_filters: list[str] | None, negative_context: str | None) -> str:
    query = topic
    if domain_filters:
        query += " " + " OR ".join(domain_filters)
    for keyword in _extract_negative_keywords(negative_context):
        query += f' -"{keyword}"'
    return query


class AcademicProblemsComponent(Component):
    display_name = "Academic Problems (SerpAPI Scholar)"
    description = "Searches Google Scholar via SerpAPI for papers describing unsolved problems related to a topic."
    icon = "graduation-cap"
    name = "AthenaAcademicProblems"

    inputs = [
        MessageTextInput(
            name="topic",
            display_name="Topic",
            info="The research topic entered by the user.",
            tool_mode=True,
        ),
        MessageTextInput(
            name="domain_filters",
            display_name="Domain Filters",
            info="Comma-separated domains/keywords to narrow the search (optional).",
            value="",
        ),
        MultilineInput(
            name="negative_context",
            display_name="Negative Context",
            info="Bulleted list of previously discovered ideas to steer away from (from the AstraDB novelty filter).",
            value="",
        ),
        IntInput(
            name="num_results",
            display_name="Max Results",
            value=10,
        ),
        SecretStrInput(
            name="serpapi_key",
            display_name="SerpAPI Key",
            info="Defaults to the SERPAPI_KEY environment variable if left blank.",
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Papers", name="papers", method="fetch_papers"),
    ]

    def fetch_papers(self) -> Data:
        key = self.serpapi_key or os.environ.get("SERPAPI_KEY")
        if not key:
            raise RuntimeError("SERPAPI_KEY is not set")

        domain_filters = [d.strip() for d in (self.domain_filters or "").split(",") if d.strip()]
        params = {
            "engine": "google_scholar",
            "q": _build_query(self.topic, domain_filters or None, self.negative_context or None),
            "api_key": key,
            "num": min(self.num_results or 10, 20),
            "as_ylo": datetime.date.today().year - 6,
        }

        try:
            results = GoogleSearch(params).get_dict()
        except Exception as exc:
            self.status = f"SerpAPI search failed: {exc}"
            raise

        papers = []
        for item in results.get("organic_results", [])[: self.num_results or 10]:
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

        self.status = f"Found {len(papers)} candidate papers."
        return Data(data={"papers": papers})
