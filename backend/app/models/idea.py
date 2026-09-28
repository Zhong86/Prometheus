"""Pydantic schemas shared by the FastAPI backend and the Langflow Structured Output node.

``IdeaPayload`` is the JSON artifact written to AstraDB (Sub-Task 2) and
returned to the frontend (Sub-Task 11). The nested models mirror the
structured output of each upstream Langflow node so every stage in the DAG
can validate against the same shapes.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Competitor(BaseModel):
    name: str
    pricing: str = Field(description="Pricing model summary, e.g. '$29/mo per seat'")
    gaps: list[str] = Field(default_factory=list, description="Missing features, poor integrations, or UX complaints")


class SynthesizedProblem(BaseModel):
    """Output of the `synthesize` node."""

    problem_statement: str
    domain: str
    target_user: str


class FeasibilityAssessment(BaseModel):
    """Output of the Technical Feasibility Evaluator node."""

    solvability_score: int = Field(ge=1, le=10)
    required_apis: list[str] = Field(default_factory=list)
    mvp_complexity: str = Field(description="One of: low, medium, high")
    reasoning: str


class IdeaPayload(BaseModel):
    """Final structured artifact produced by the Dual Spec & Artifact Generator node."""

    niche: str
    problem_statement: str
    target_user: str
    feasibility_score: int = Field(ge=1, le=10)
    proof_of_pain_url: str
    tech_stack: list[str] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    market_gap_summary: str
