"""Langflow node: public_friction.

Wraps Tavily advanced search across review/forum sites (Capterra, G2, Reddit,
Trustpilot) to surface raw micro-level user complaints for a topic.

Self-contained on purpose — see the note in academic_problems.py. The same
search logic also lives in backend/app/tools/public_friction.py for the
FastAPI side; keep both in sync if the query-building logic changes.
"""
from __future__ import annotations

import os

from tavily import TavilyClient

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output, SecretStrInput
from lfx.schema import Data

PAIN_SITES = ["capterra.com", "g2.com", "reddit.com", "trustpilot.com"]
PAIN_PHRASES = [
    '"doesn\'t work"',
    '"so clunky"',
    '"wish it could"',
    '"biggest frustration"',
    "clunky",
    "workaround",
]


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


def _build_queries(topic: str, negative_keywords: list[str] | None) -> list[str]:
    exclusions = "".join(f' -"{kw}"' for kw in (negative_keywords or [])[:5])
    phrase_clause = " OR ".join(PAIN_PHRASES)
    return [f'site:{site} "{topic}" ({phrase_clause}){exclusions}' for site in PAIN_SITES]


class PublicFrictionComponent(Component):
    display_name = "Public Friction (Tavily)"
    description = "Searches Capterra, G2, Reddit, and Trustpilot for raw complaints and reviews related to a topic."
    icon = "message-square-warning"
    name = "AthenaPublicFriction"

    inputs = [
        MessageTextInput(
            name="topic",
            display_name="Topic",
            tool_mode=True,
        ),
        MultilineInput(
            name="negative_context",
            display_name="Negative Context",
            info="Bulleted list of previously discovered ideas to steer away from (from the AstraDB novelty filter).",
            value="",
        ),
        IntInput(
            name="max_results_per_site",
            display_name="Max Results Per Site",
            value=4,
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

    def fetch_complaints(self) -> Data:
        key = self.tavily_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set")

        client = TavilyClient(api_key=key)
        negative_keywords = _extract_negative_keywords(self.negative_context or None)

        complaints: list[dict] = []
        try:
            for query in _build_queries(self.topic, negative_keywords):
                response = client.search(
                    query=query,
                    search_depth="advanced",
                    include_raw_content=True,
                    max_results=self.max_results_per_site or 4,
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
        except Exception as exc:
            self.status = f"Tavily search failed: {exc}"
            raise

        self.status = f"Found {len(complaints)} complaints across review/forum sites."
        return Data(data={"complaints": complaints})
