"""Langflow node: academic_problems.

Wraps SerpAPI's google_scholar engine to surface candidate unsolved academic
problems for a topic. Wire the `papers` output into a Prompt + Google
Generative AI Model pair (see /flows/prompts/academic_problem_extraction.md)
to turn each abstract into a concrete `problem_statement`.
"""
from __future__ import annotations

from . import _bootstrap  # noqa: F401  (must run before the app.* import below)
from app.tools.academic_problems import search_academic_problems

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output, SecretStrInput
from lfx.schema import Data


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
        domain_filters = [d.strip() for d in (self.domain_filters or "").split(",") if d.strip()]
        try:
            papers = search_academic_problems(
                topic=self.topic,
                domain_filters=domain_filters or None,
                negative_context=self.negative_context or None,
                num_results=self.num_results or 10,
                api_key=self.serpapi_key or None,
            )
        except Exception as exc:
            self.status = f"SerpAPI search failed: {exc}"
            raise

        self.status = f"Found {len(papers)} candidate papers."
        return Data(data={"papers": papers})
