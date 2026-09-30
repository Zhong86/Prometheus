"""Langflow node: idea_report.

Joins the three Structured Output nodes (Synthesize, Competition Analysis,
Feasibility) — each returning one object per idea — by `idea_id` into
{"ideas": [...]} for Chat Output / the FastAPI backend, and emits one document
per idea for the Save Ideas (Astra DB) node, so later runs can steer away from
ideas already found. No LLM here — it's a deterministic merge so nothing
upstream gets lost.
"""
from __future__ import annotations

import datetime
import json
import re

from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, MessageTextInput, Output
from lfx.schema.dataframe import DataFrame
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


def _split_pipes(entry, n: int) -> list[str]:
    parts = [p.strip() for p in str(entry).split("|")]
    parts += [""] * (n - len(parts))
    return parts[: n - 1] + ["|".join(parts[n - 1 :]).strip()]


def _parse_competitor(entry) -> dict:
    """Turn "name | url | pricing | gap 1; gap 2" into a Competitor-shaped dict.

    Competition Analysis emits strings because Gemini returns empty objects
    for free-form `dict` schema fields.
    """
    if isinstance(entry, dict):
        return entry
    name, url, pricing, gaps = _split_pipes(entry, 4)
    return {
        "name": name,
        "url": "" if url.lower() == "unknown" else url,
        "pricing": pricing or "unknown",
        "gaps": [g.strip() for g in gaps.split(";") if g.strip()],
    }


SOURCE_NAMES = {"news.ycombinator.com": "hackernews", "ycombinator": "hackernews", "scholar": "paper"}


def _source_name(source: str) -> str:
    """Normalise "reddit.com" / "news.ycombinator.com" etc. to the short names the prompt asks for."""
    source = source.strip().lower()
    if source in SOURCE_NAMES:
        return SOURCE_NAMES[source]
    return source.removeprefix("www.").split(".")[0]


def _parse_evidence(entry) -> dict:
    """Turn "source | finding | url" into {source, finding, url} (same reason as above)."""
    if isinstance(entry, dict):
        return entry
    source, finding, url = _split_pipes(entry, 3)
    return {"source": _source_name(source), "finding": finding, "url": url}


SOLUTION_TYPES = ("ai_automation", "software", "iot", "other_tech")
COMPLEXITIES = ("low", "medium", "high")


def _pick(value, allowed: tuple[str, ...]):
    """Snap an enum-like field to its allowed value.

    flash-lite occasionally leaks the next field's name into the value
    (e.g. "software,target_user:"), so keep the first allowed value it contains.
    """
    found = re.search("|".join(allowed), str(value or "").lower())
    return found.group(0) if found else value


def _by_id(items: list[dict]) -> dict[str, dict]:
    return {str(item.get("idea_id", i)): item for i, item in enumerate(items, 1)}


class IdeaReportComponent(Component):
    display_name = "Idea Report"
    description = "Joins Synthesize, Competition Analysis and Feasibility outputs by idea_id into one JSON report."
    icon = "file-json"
    name = "AthenaIdeaReport"

    inputs = [
        HandleInput(
            name="synthesis",
            display_name="Synthesis",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        HandleInput(
            name="competition",
            display_name="Competition Analysis",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        HandleInput(
            name="feasibility",
            display_name="Feasibility",
            input_types=["JSON", "Data", "Message"],
            required=True,
        ),
        MessageTextInput(
            name="topic",
            display_name="Topic",
            info="The research topic, stored with each saved idea.",
            value="",
        ),
    ]

    outputs = [
        Output(display_name="Report", name="report", method="build_report"),
        Output(display_name="Idea Documents", name="documents", method="build_documents"),
    ]

    def _ideas(self) -> list[dict]:
        competition = _by_id(_as_list(self.competition))
        feasibility = _by_id(_as_list(self.feasibility))

        ideas = []
        for i, synthesis in enumerate(_as_list(self.synthesis), 1):
            idea_id = str(synthesis.get("idea_id", i))
            synthesis.pop("competitor_queries", None)  # search plumbing, not part of the idea
            synthesis["evidence"] = [_parse_evidence(e) for e in synthesis.get("evidence") or []]
            comp = {k: v for k, v in competition.get(idea_id, {}).items() if k != "idea_id"}
            comp["competitors"] = [_parse_competitor(c) for c in comp.get("competitors") or []]
            feas = {k: v for k, v in feasibility.get(idea_id, {}).items() if k != "idea_id"}
            idea = {**synthesis, "idea_id": i, **comp, **feas}
            if "solution_type" in idea:
                idea["solution_type"] = _pick(idea["solution_type"], SOLUTION_TYPES)
            if "mvp_complexity" in idea:
                idea["mvp_complexity"] = _pick(idea["mvp_complexity"], COMPLEXITIES)
            ideas.append(idea)
        return ideas

    def build_report(self) -> Message:
        report = {"ideas": self._ideas()}
        self.status = report
        return Message(text=json.dumps(report, indent=2, ensure_ascii=False))

    def build_documents(self) -> DataFrame:
        """One row per idea for Astra DB ingestion.

        `text` is what gets embedded and later matched against a new run's topic
        (the Astra search at the start of the flow), so it holds the problem,
        user and solution. Everything else is stored as metadata; the full idea
        is kept as JSON in `idea`.
        """
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        rows = []
        for idea in self._ideas():
            rows.append(
                {
                    "text": (
                        f"{idea.get('problem_statement', '')} "
                        f"Target user: {idea.get('target_user', '')}. "
                        f"Solution: {idea.get('solution_approach', '')}"
                    ),
                    "topic": self.topic or "",
                    "domain": idea.get("domain", ""),
                    "solution_type": idea.get("solution_type", ""),
                    "solvability_score": idea.get("solvability_score"),
                    "mvp_complexity": idea.get("mvp_complexity", ""),
                    "created_at": created_at,
                    "idea": json.dumps(idea, ensure_ascii=False),
                }
            )
        self.status = f"{len(rows)} idea documents"
        return DataFrame(rows)
