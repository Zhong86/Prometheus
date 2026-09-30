from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.langflow import LangflowError, run_research

router = APIRouter(prefix="/api")


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)


class ResearchResponse(BaseModel):
    topic: str
    ideas: list[dict[str, Any]]


@router.post("/research", response_model=ResearchResponse)
async def research(req: ResearchRequest) -> ResearchResponse:
    topic = req.topic.strip()
    try:
        ideas = await run_research(topic)
    except LangflowError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ResearchResponse(topic=topic, ideas=ideas)
