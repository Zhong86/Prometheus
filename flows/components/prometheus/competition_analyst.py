"""Langflow node: competition_analyst.

Wraps Tavily search to find existing SaaS/products that already solve the
synthesized problem statement. Wire the `results` output into a Prompt +
Model pair (see /flows/prompts/competition_analyst.md) to extract structured
competitor data and a market-gap summary.

Self-contained on purpose — see the note in academic_problems.py. The same
search logic also lives in backend/app/tools/competition_analyst.py for the
FastAPI side; keep both in sync if the query-building logic changes.
"""
from __future__ import annotations

import os

from tavily import TavilyClient

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, Output, SecretStrInput
from lfx.schema import Data


class CompetitionAnalystComponent(Component):
    display_name = "Competition Analyst (Tavily)"
    description = "Searches for existing products/competitors solving a synthesized problem statement."
    icon = "search"
    name = "AthenaCompetitionAnalyst"

    inputs = [
        MessageTextInput(
            name="problem_statement",
            display_name="Problem Statement",
            info="The synthesized problem statement from the synthesize node.",
            tool_mode=True,
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            value=8,
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

    def fetch_competitors(self) -> Data:
        key = self.tavily_key or os.environ.get("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("TAVILY_API_KEY is not set")

        client = TavilyClient(api_key=key)
        query = f'"{self.problem_statement}" software product OR SaaS OR app pricing reviews'

        try:
            response = client.search(
                query=query,
                search_depth="advanced",
                include_raw_content=True,
                max_results=self.max_results or 8,
            )
        except Exception as exc:
            self.status = f"Tavily search failed: {exc}"
            raise

        results = [
            {
                "source": result.get("url", ""),
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "raw_content": result.get("raw_content", ""),
                "score": result.get("score", 0.0),
            }
            for result in response.get("results", [])
        ]

        self.status = f"Found {len(results)} candidate competitors/products."
        return Data(data={"results": results})
