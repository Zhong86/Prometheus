"""Client for the Langflow run API: sends a topic through the Prometheus flow."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

# The flow does 4 LLM calls plus ~14 searches, so a run takes minutes.
RUN_TIMEOUT = httpx.Timeout(900.0, connect=10.0)


class LangflowError(RuntimeError):
    """Langflow was unreachable, returned an error, or produced output we can't read."""


def _chat_text(result: dict[str, Any]) -> str:
    """Pull the Chat Output message text out of a /run response."""
    try:
        out = result["outputs"][0]["outputs"][0]
        message = out["results"]["message"]
        return message.get("text") or message["data"]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LangflowError(f"Unexpected Langflow response shape: {str(result)[:300]}") from exc


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return text.strip()


async def run_research(topic: str) -> list[dict[str, Any]]:
    """Run the flow for ``topic`` and return its list of ideas."""
    base = os.environ.get("LANGFLOW_BASE_URL", "http://localhost:7860").rstrip("/")
    flow_id = os.environ.get("LANGFLOW_FLOW_ID")
    if not flow_id:
        raise LangflowError("LANGFLOW_FLOW_ID is not set")

    headers = {}
    if api_key := os.environ.get("LANGFLOW_API_KEY"):
        headers["x-api-key"] = api_key

    payload = {"input_value": topic, "input_type": "chat", "output_type": "chat"}
    try:
        async with httpx.AsyncClient(timeout=RUN_TIMEOUT) as client:
            resp = await client.post(f"{base}/api/v1/run/{flow_id}", json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise LangflowError(f"Could not reach Langflow at {base}: {exc!r}") from exc
    if resp.status_code != 200:
        raise LangflowError(f"Langflow returned {resp.status_code}: {resp.text[:300]}")

    text = _chat_text(resp.json())
    try:
        ideas = json.loads(_strip_fence(text))["ideas"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LangflowError(f"Flow output was not an ideas report: {text[:300]}") from exc
    return ideas
