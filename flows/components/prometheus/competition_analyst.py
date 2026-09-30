"""Langflow node: competition_analyst.

Runs the competitor queries written by the Synthesize node (see
/flows/prompts/synthesize.md, field `competitor_queries`) through Tavily —
separately for each idea when Synthesize returned several — and returns the
hits grouped per idea as compact text for the Competition Analysis node. No
LLM here — Synthesize decides *what* to search, this node only executes it.

Self-contained on purpose — see the note in academic_problems.py. The same
search logic also lives in backend/app/tools/competition_analyst.py for the
FastAPI side; keep both in sync if the query-building logic changes.
"""
from __future__ import annotations

import json
import os

from tavily import TavilyClient

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, HandleInput, IntInput, MessageTextInput, Output, SecretStrInput
from lfx.schema.message import Message

RAW_CONTENT_CHARS = 1500
EXCERPT_CHARS = 500


def _coerce_list(raw, limit: int) -> list[str]:
    """Accept a list, a JSON-encoded list, or newline-separated text."""
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


def _ideas_with_queries(value, key: str, limit: int) -> list[tuple[str, list[str]]]:
    """Return (heading, queries) per idea from a Structured Output (Data) or a Message.

    Synthesize returns one object, or several wrapped as {"results": [...]}.
    A Message is treated as one query per line for a single unnamed idea.
    """
    if isinstance(value, Message):  # checked first: Message subclasses Data
        return [("", _coerce_list(value.text, limit))]

    data = getattr(value, "data", value) or {}
    items = data["results"] if isinstance(data.get("results"), list) else [data]
    ideas = []
    for i, item in enumerate(items, 1):
        heading = f"Idea {item.get('idea_id', i)}: {item.get('problem_statement', '')}".strip(": ")
        ideas.append((heading, _coerce_list(item.get(key, ""), limit)))
    return ideas


class CompetitionAnalystComponent(Component):
    display_name = "Competition Analyst (Tavily)"
    description = "Runs Synthesize-written competitor queries via Tavily, per idea, to find existing products."
    icon = "search"
    name = "AthenaCompetitionAnalyst"

    inputs = [
        HandleInput(
            name="queries",
            display_name="Queries",
            info="Synthesize output (JSON, one or several ideas) or a Message with one query per line.",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        MessageTextInput(
            name="queries_key",
            display_name="Queries Key",
            info="Field to read from each Synthesize idea.",
            value="competitor_queries",
            advanced=True,
        ),
        IntInput(
            name="max_queries",
            display_name="Max Queries Per Idea",
            value=2,
            advanced=True,
        ),
        IntInput(
            name="results_per_query",
            display_name="Results Per Query",
            value=4,
        ),
        BoolInput(
            name="include_raw_content",
            display_name="Include Raw Content",
            info=f"Append up to {RAW_CONTENT_CHARS} chars of page text per hit. Costs a lot of tokens downstream.",
            value=False,
            advanced=True,
        ),
        SecretStrInput(
            name="tavily_key",
            display_name="Tavily API Key",
            info="Defaults to the TAVILY_API_KEY environment variable if left blank.",
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Results", name="results", method="fetch_competitors"),
    ]

    def fetch_competitors(self) -> Message:
        key = self.tavily_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set")

        ideas = _ideas_with_queries(self.queries, self.queries_key or "competitor_queries", self.max_queries or 2)
        if not any(queries for _, queries in ideas):
            raise ValueError(f"No queries found under '{self.queries_key}' in the Synthesize output.")

        client = TavilyClient(api_key=key)
        sections: list[str] = []
        total = searches = 0
        for heading, queries in ideas:
            seen: set[str] = set()  # per idea: the same product can compete with several ideas
            blocks: list[str] = []
            for query in queries:
                searches += 1
                try:
                    response = client.search(
                        query=query,
                        search_depth="advanced",
                        include_raw_content=bool(self.include_raw_content),
                        max_results=self.results_per_query or 4,
                    )
                except Exception as exc:
                    self.status = f"Tavily search failed on {query!r}: {exc}"
                    raise

                for result in response.get("results", []):
                    url = result.get("url", "")
                    if url in seen:
                        continue
                    seen.add(url)
                    total += 1
                    block = (
                        f"[{total}] {result.get('title', '')}\n"
                        f"URL: {url}\n"
                        f"Excerpt: {(result.get('content') or '')[:EXCERPT_CHARS]}"
                    )
                    raw = (result.get("raw_content") or "")[:RAW_CONTENT_CHARS]
                    if raw:
                        block += f"\nPage text: {raw}"
                    blocks.append(block)

            body = "\n\n".join(blocks) if blocks else "No competitor results found."
            sections.append(f"===== {heading} =====\n{body}" if heading else body)

        self.status = f"Found {total} candidate competitors/products from {searches} searches across {len(ideas)} ideas."
        return Message(text="\n\n".join(sections))
