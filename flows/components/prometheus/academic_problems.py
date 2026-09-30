"""Langflow node: academic_problems.

Runs the Google Scholar queries written by the Query Planner (see
/flows/prompts/query_planner.md) through SerpAPI and returns the papers as
compact text for the Synthesize node. No LLM here — the planner decides
*what* to search, this node only executes it.

Self-contained on purpose: Langflow loads each component file through its own
bundle-module mechanism rather than a normal package import, so reaching
across to backend/app/tools/* via a sys.path trick doesn't reliably work at
runtime (fails with "ModuleNotFoundError: No module named 'app'"). The same
search logic also lives in backend/app/tools/academic_problems.py for the
FastAPI side; keep both in sync if the query-building logic changes.
"""
from __future__ import annotations

import datetime
import json
import os

from serpapi import GoogleSearch

from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.schema.message import Message


def _coerce_queries(value, key: str, limit: int) -> list[str]:
    """Pull a list of query strings out of a Structured Output (Data) or a Message.

    Accepts a list, a JSON-encoded list, or newline-separated text under `key`.
    """
    raw = value
    if isinstance(value, Message):  # checked first: Message subclasses Data
        raw = value.text
    elif hasattr(value, "data"):  # Data / JSON from Structured Output
        data = value.data or {}
        if "results" in data and key not in data:  # model returned several objects
            data = (data["results"] or [{}])[0]
        raw = data.get(key, "")

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            raw = raw.splitlines()
    if isinstance(raw, str):
        raw = [raw]

    queries: list[str] = []
    for item in raw or []:
        query = str(item).strip().lstrip("-").strip()
        if query and query not in queries:
            queries.append(query)
    return queries[:limit]


class AcademicProblemsComponent(Component):
    display_name = "Academic Problems (SerpAPI Scholar)"
    description = "Runs planner-written Google Scholar queries via SerpAPI and returns the papers found."
    icon = "graduation-cap"
    name = "AthenaAcademicProblems"

    inputs = [
        HandleInput(
            name="queries",
            display_name="Queries",
            info="Query Planner output (JSON) or a Message with one query per line.",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        MessageTextInput(
            name="queries_key",
            display_name="Queries Key",
            info="Field to read from the Query Planner JSON.",
            value="scholar_queries",
            advanced=True,
        ),
        IntInput(
            name="max_queries",
            display_name="Max Queries",
            value=3,
            advanced=True,
        ),
        IntInput(
            name="results_per_query",
            display_name="Results Per Query",
            value=5,
        ),
        IntInput(
            name="years_back",
            display_name="Years Back",
            info="Only papers published in the last N years.",
            value=6,
            advanced=True,
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

    def fetch_papers(self) -> Message:
        key = self.serpapi_key or os.environ.get("SERPAPI_KEY")
        if not key:
            raise RuntimeError("SERPAPI_KEY is not set")

        queries = _coerce_queries(self.queries, self.queries_key or "scholar_queries", self.max_queries or 3)
        if not queries:
            raise ValueError(f"No queries found under '{self.queries_key}' in the Query Planner output.")

        papers: list[dict] = []
        seen: set[str] = set()
        for query in queries:
            params = {
                "engine": "google_scholar",
                "q": query,
                "api_key": key,
                "num": min(self.results_per_query or 5, 20),
                "as_ylo": datetime.date.today().year - (self.years_back or 6),
            }
            try:
                results = GoogleSearch(params).get_dict()
            except Exception as exc:
                self.status = f"SerpAPI search failed on {query!r}: {exc}"
                raise
            # SerpAPI reports failures (bad key, no credits) in the body, not as an exception.
            # "hasn't returned any results" just means an empty result set.
            error = results.get("error")
            if error and "hasn't returned any results" not in error:
                self.status = f"SerpAPI error on {query!r}: {error}"
                raise RuntimeError(f"SerpAPI error: {error}")

            for item in results.get("organic_results", []):
                dedupe_key = item.get("link") or item.get("title", "")
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                cited_by = item.get("inline_links", {}).get("cited_by", {})
                papers.append(
                    {
                        "query": query,
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "abstract": item.get("snippet", ""),
                        "published": item.get("publication_info", {}).get("summary", ""),
                        "citations": cited_by.get("total", 0) if cited_by else 0,
                    }
                )

        self.status = f"Found {len(papers)} papers across {len(queries)} queries."
        if not papers:
            return Message(text="No papers found.")

        blocks = [
            f"[{i}] {p['title']}\n"
            f"Published: {p['published']} | {p['citations']} citations\n"
            f"URL: {p['link']}\n"
            f"Abstract: {p['abstract']}"
            for i, p in enumerate(papers, 1)
        ]
        return Message(text="\n\n".join(blocks))
