"""Helpers for working with the AstraDB novelty-filter negative-context string.

The full novelty filter (embedding + AstraDB query) is built in Sub-Task 2 —
``app/db/astra.py``. These helpers only handle formatting/parsing so the search
tools and Gemini prompts don't need to know how the string was produced.
"""
from __future__ import annotations


def format_negative_context(similar_ideas: list[dict]) -> str:
    """Format previously stored ideas as a bulleted 'avoid these' block for prompts."""
    if not similar_ideas:
        return "None yet — this is a fresh topic."
    lines = []
    for idea in similar_ideas:
        niche = idea.get("niche") or idea.get("problem_statement", "Unknown idea")
        lines.append(f"- {niche}")
    return "\n".join(lines)


def extract_negative_keywords(negative_context: str | None, limit: int = 5) -> list[str]:
    """Pull short exclusion phrases out of a negative_context block for search-query filtering."""
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
