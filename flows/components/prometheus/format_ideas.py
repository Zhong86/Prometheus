"""Langflow node: format_ideas.

Renders a Structured Output that returned several objects (one per idea)
into text for the next prompt, one block per idea. The built-in Parser can't
do this: Structured Output wraps multiple objects as {"results": [...]} and
Parser only formats the top-level keys. No LLM here.
"""
from __future__ import annotations

import json

from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, MultilineInput, Output
from lfx.schema.message import Message


def _as_list(value) -> list[dict]:
    """Normalise Structured Output (one object or {"results": [...]}) to a list of dicts."""
    if value is None:
        return []
    if isinstance(value, Message):  # checked first: Message subclasses Data
        try:
            value = json.loads(value.text)
        except (json.JSONDecodeError, ValueError, TypeError):
            return [{"text": value.text}]
    data = getattr(value, "data", value) or {}
    if isinstance(data, list):
        return [dict(d) for d in data]
    if "results" in data and isinstance(data["results"], list):
        return [dict(d) for d in data["results"]]
    return [dict(data)]


class _Blank(dict):
    def __missing__(self, key):
        return ""


def _render(template: str, item: dict) -> str:
    values = _Blank({k: "; ".join(map(str, v)) if isinstance(v, list) else v for k, v in item.items()})
    return template.format_map(values)


class FormatIdeasComponent(Component):
    display_name = "Format Ideas"
    description = "Formats a multi-object Structured Output into one text block per idea."
    icon = "list"
    name = "AthenaFormatIdeas"

    inputs = [
        HandleInput(
            name="data",
            display_name="Data",
            info="Structured Output (one object or several).",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        MultilineInput(
            name="header",
            display_name="Header",
            info="Rendered above each object. Use {field} placeholders.",
            value="===== Idea {idea_id} =====",
        ),
        MultilineInput(
            name="template",
            display_name="Template",
            info="Rendered for each object. Use {field} placeholders; lists are joined with '; '.",
            value="{problem_statement}",
        ),
    ]

    outputs = [
        Output(display_name="Formatted Text", name="formatted", method="format_ideas"),
    ]

    def format_ideas(self) -> Message:
        items = _as_list(self.data)
        for i, item in enumerate(items, 1):
            item.setdefault("idea_id", i)
        blocks = [f"{_render(self.header or '', item)}\n{_render(self.template or '', item)}".strip() for item in items]
        text = "\n\n".join(blocks)
        self.status = text
        return Message(text=text)
