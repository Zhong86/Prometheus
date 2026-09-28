"""Langflow node: competition_analyst.

Wraps Tavily search to find existing SaaS/products that already solve the
synthesized problem statement. Wire the `results` output into a Prompt +
Model pair (see /flows/prompts/competition_analyst.md) to extract structured
competitor data and a market-gap summary.
"""
from __future__ import annotations

from . import _bootstrap  # noqa: F401
from app.tools.competition_analyst import search_competitors

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
        try:
            results = search_competitors(
                problem_statement=self.problem_statement,
                max_results=self.max_results or 8,
                api_key=self.tavily_key or None,
            )
        except Exception as exc:
            self.status = f"Tavily search failed: {exc}"
            raise

        self.status = f"Found {len(results)} candidate competitors/products."
        return Data(data={"results": results})
