"""Langflow node: public_friction.

Wraps Tavily advanced search across review/forum sites (Capterra, G2, Reddit,
Trustpilot) to surface raw micro-level user complaints for a topic.
"""
from __future__ import annotations

from . import _bootstrap  # noqa: F401
from app.tools.public_friction import search_public_friction

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output, SecretStrInput
from lfx.schema import Data


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
        try:
            complaints = search_public_friction(
                topic=self.topic,
                negative_context=self.negative_context or None,
                max_results_per_site=self.max_results_per_site or 4,
                api_key=self.tavily_key or None,
            )
        except Exception as exc:
            self.status = f"Tavily search failed: {exc}"
            raise

        self.status = f"Found {len(complaints)} complaints across review/forum sites."
        return Data(data={"complaints": complaints})
