# Node: competition_analysis (LLM call 3 of 4)

**Structured Output** component (category: LLM Operations). For each of the
3 ideas, pulls real competitors out of that idea's Competition Analyst
search results and names the gap none of them fill. Extraction only —
feasibility scoring is a separate node so each prompt stays focused and
each schema stays small. Returns one object per idea, keyed by `idea_id`.

- **Input Message** (`input_value`) ← Prompt Template below.
- **Language Model** — Google Generative AI, `gemini-3.5-flash-lite`.
- **Format Instructions** (`system_prompt`) ← text below.
- **Schema Name** — `CompetitionAnalysis`.
- **Output Schema** — see table. Field names match `IdeaPayload.competitors`
  / `market_gap_summary` in `backend/app/models/idea.py`.
  `competitors` is a list of pipe-separated strings rather than `dict`:
  Gemini returns empty `{}` objects for free-form `dict` fields. **Idea
  Report** parses the strings back into `{name, url, pricing, gaps}`.
- **Output** (`structured_output`, JSON) →
  - **Format Ideas** (header/template below) → Feasibility prompt as
    `{competition}`
  - `competition` on **Idea Report**

## Output Schema

| Name | Type | As List | Description |
|---|---|---|---|
| `idea_id` | int | False | The idea this analysis is for: 1, 2 or 3, matching the input. |
| `competitors` | str | True | One entry per real competitor, formatted exactly as: `name \| url \| pricing \| gap 1; gap 2`. Use "unknown" for missing pricing or url; "open source" as pricing for free OSS projects. |
| `market_gap_summary` | str | False | 2-3 sentences on what none of the competitors do well — the opening for this idea. |

## Prompt Template (feeds `input_value`)

```
Ideas:
{idea}

Competitor search results (grouped by idea):
{competitor_results}
```

- `{idea}` ← Synthesize → Format Ideas.
- `{competitor_results}` ← Competition Analyst `results`.

## Format Ideas template (Structured Output → `{competition}` in Feasibility)

Header:

```
===== Idea {idea_id} =====
```

Template:

```
Competitors (name | url | pricing | gaps): {competitors}
Market gap: {market_gap_summary}
```

## Format Instructions (feeds `system_prompt`)

```
You are a market analyst helping a software developer decide which ideas
are worth building. You are given 3 ideas (problem statement, domain,
target user, proposed solution), each headed "===== Idea N =====", and raw
web search results about possibly competing products, grouped under a
heading per idea.

Return exactly 3 objects — one per idea, with the same idea_id. Analyse
each idea against its own group of search results; a product found for one
idea may also be listed for another if it genuinely competes with both.

For each idea, identify distinct, genuine competitors — anything the target
user could adopt instead of the proposed solution: software products, SaaS,
AI/automation tools, open-source projects, IoT devices or platforms, and
features built into larger suites the user already has. Skip blog posts,
listicles, news articles, agencies, consultancies and unrelated noise — but
if a listicle names real products, you may include those products.

Write one competitors entry per real competitor, formatted exactly as:

  name | url | pricing | gap 1; gap 2

- url: exactly one URL copied from the results — the product's own site or
  repo if it appears, otherwise the result URL; "unknown" if neither.
- pricing: the pricing model as stated, "open source" for free OSS
  projects, or "unknown".
- gaps: missing features, poor integrations or APIs, weak automation, or
  recurring UX complaints mentioned in the source material, separated by
  semicolons. Only list gaps the results support — don't guess.

Up to 5 competitors per idea; an empty list is fine if the results show
none.

Then write market_gap_summary: what none of the competitors currently do
well for this target user, and whether the proposed solution actually
targets that gap. That gap is the opening for this idea.

Return exactly 3 objects matching the schema. No commentary.
```
