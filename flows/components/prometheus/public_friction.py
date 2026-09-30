"""Langflow node: public_friction.

Runs the platform-specific complaint queries written by the Query Planner
(see /flows/prompts/query_planner.md) through Tavily — one search per site,
so a single noisy site (usually Reddit) can't crowd out the others — and
returns the hits grouped by platform for the Synthesize node. No LLM here —
the planner decides *what* to search, this node only executes it.

Self-contained on purpose — see the note in academic_problems.py. The same
search logic also lives in backend/app/tools/public_friction.py for the
FastAPI side; keep both in sync if the query-building logic changes.
"""
from __future__ import annotations

import json
import os
import re

from tavily import TavilyClient

from lfx.custom.custom_component.component import Component
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    IntInput,
    MultilineInput,
    Output,
    SecretStrInput,
)
from lfx.schema.message import Message

# One line per site: "<domain> = <Query Planner field>". A field can feed several sites.
SITE_GROUPS = """reddit.com = reddit_queries
news.ycombinator.com = hackernews_queries
capterra.com = capterra_queries
producthunt.com = producthunt_queries"""
RAW_CONTENT_CHARS = 1500
EXCERPT_CHARS = 500


def _coerce_queries(value, key: str, limit: int) -> list[str]:
    """Pull a list of query strings out of a Structured Output (Data) or a Message.

    Accepts a list, a JSON-encoded list, or newline-separated text under `key`.
    A Message is treated as one query per line for every key.
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


def _parse_site_groups(text: str) -> list[tuple[str, str]]:
    groups = []
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        site, key = (part.strip() for part in line.split("=", 1))
        if site and key:
            groups.append((site, key))
    return groups


def _clean(text: str) -> str:
    # HN/forum pages come back with nav chrome like "| | | 382 points by x | hide | past |".
    return re.sub(r"(?:\s*\|\s*){2,}", " | ", text or "").strip(" |")


class PublicFrictionComponent(Component):
    display_name = "Public Friction (Tavily)"
    description = "Runs planner-written complaint queries via Tavily, one search per review/forum site."
    icon = "message-square-warning"
    name = "AthenaPublicFriction"

    inputs = [
        HandleInput(
            name="queries",
            display_name="Queries",
            info="Query Planner output (JSON), or a Message with one query per line to run on every site.",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        MultilineInput(
            name="site_groups",
            display_name="Site Groups",
            info="One line per site: '<domain> = <Query Planner field>'. Each site is searched separately.",
            value=SITE_GROUPS,
            advanced=True,
        ),
        IntInput(
            name="max_queries",
            display_name="Max Queries Per Site",
            value=2,
            advanced=True,
        ),
        IntInput(
            name="results_per_query",
            display_name="Results Per Query",
            value=3,
        ),
        DropdownInput(
            name="search_depth",
            display_name="Search Depth",
            info="'advanced' returns better excerpts but costs 2 Tavily credits per search instead of 1.",
            options=["basic", "advanced"],
            value="advanced",
            advanced=True,
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
        Output(display_name="Complaints", name="complaints", method="fetch_complaints"),
    ]

    def fetch_complaints(self) -> Message:
        key = self.tavily_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set")

        groups = _parse_site_groups(self.site_groups or SITE_GROUPS)
        if not groups:
            raise ValueError("Site Groups is empty — expected lines like 'reddit.com = reddit_queries'.")

        client = TavilyClient(api_key=key)
        seen: set[str] = set()
        sections: list[str] = []
        total = searches = 0
        for site, queries_key in groups:
            queries = _coerce_queries(self.queries, queries_key, self.max_queries or 2)
            hits: list[dict] = []
            for query in queries:
                searches += 1
                try:
                    response = client.search(
                        query=query,
                        search_depth=self.search_depth or "advanced",
                        include_domains=[site],
                        include_raw_content=bool(self.include_raw_content),
                        max_results=self.results_per_query or 3,
                    )
                except Exception as exc:
                    self.status = f"Tavily search failed on {site} / {query!r}: {exc}"
                    raise

                for result in response.get("results", []):
                    url = result.get("url", "")
                    if url in seen:
                        continue
                    seen.add(url)
                    hits.append(
                        {
                            "source": url,
                            "title": result.get("title", ""),
                            "quote": _clean(result.get("content", ""))[:EXCERPT_CHARS],
                            "raw_content": _clean(result.get("raw_content") or "")[:RAW_CONTENT_CHARS],
                        }
                    )

            blocks = []
            for c in hits:
                total += 1
                block = f"[{total}] {c['title']}\nURL: {c['source']}\nExcerpt: {c['quote']}"
                if c["raw_content"]:
                    block += f"\nPage text: {c['raw_content']}"
                blocks.append(block)
            body = "\n\n".join(blocks) if blocks else "No results."
            sections.append(f"===== Source: {site} =====\n{body}")

        self.status = f"Found {total} complaints from {searches} searches across {len(groups)} sites."
        return Message(text="\n\n".join(sections))
