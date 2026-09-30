# Node: feasibility (LLM call 4 of 4)

**Structured Output** component (category: LLM Operations). Scores how
buildable each of the 3 ideas is for a small dev team — specifically the
version that fills the market gap found by Competition Analysis, not the
problem in general. Returns one object per idea, keyed by `idea_id`.

- **Input Message** (`input_value`) ← Prompt Template below.
- **Language Model** — Google Generative AI, `gemini-3.5-flash-lite`.
- **Format Instructions** (`system_prompt`) ← text below.
- **Schema Name** — `FeasibilityAssessment`.
- **Output Schema** — see table. Matches `FeasibilityAssessment` in
  `backend/app/models/idea.py`.
- **Output** (`structured_output`, JSON) → `feasibility` on **Idea Report**.

## Output Schema

| Name | Type | As List | Description |
|---|---|---|---|
| `idea_id` | int | False | The idea this assessment is for: 1, 2 or 3, matching the input. |
| `solvability_score` | int | False | 1-10, how buildable the MVP is by 1-3 developers; 10 = trivial, 1 = research-grade difficulty. |
| `required_apis` | str | True | Real, named APIs, SDKs, models or hardware the MVP needs, e.g. "Google Document AI", "Twilio SMS API", "ESP32", "AWS IoT Core". |
| `mvp_complexity` | str | False | Exactly one of: low, medium, high. |
| `reasoning` | str | False | 2-4 sentences justifying the score, naming the riskiest technical assumption. |

## Prompt Template (feeds `input_value`)

```
Ideas:
{idea}

Competitive landscape (per idea):
{competition}
```

- `{idea}` ← Synthesize → Format Ideas (same node that feeds Competition Analysis).
- `{competition}` ← Competition Analysis → Format Ideas.

## Format Instructions (feeds `system_prompt`)

```
You are a pragmatic technical architect scoping an MVP for a team of 1-3
software developers. You are given 3 ideas (problem, domain, target user,
solution type and proposed solution), each headed "===== Idea N =====", and
each idea's competitive landscape (existing competitors and the market gap
they leave open) under the same heading.

Return exactly 3 objects — one per idea, with the same idea_id. Score each
idea on its own merits; don't rank them against each other.

For each idea, assess how buildable an MVP that fills its market gap is for
this team within roughly 1-3 months. Judge it by its solution type:
- software: data access and integrations are usually the hard part — does
  the system it must connect to have a usable public API?
- ai_automation: is the model accuracy it needs achievable with current
  hosted models or modest fine-tuning, and what happens when it's wrong?
- iot: can it be built from off-the-shelf boards and sensors, and how hard
  are power, connectivity and field deployment?
- other_tech: whatever the dominant technical risk is.

Score solvability_score 1-10 (10 = trivial CRUD app, 1 = requires
research-grade ML, custom hardware or infrastructure that doesn't exist
yet). List required_apis: the real, named APIs, SDKs, hosted models or
hardware the MVP needs — only ones that actually exist and that this idea
really needs, not a generic stack (don't add payments, email or SMS unless
the core workflow depends on them). Set mvp_complexity to exactly one of
"low", "medium", "high". Write reasoning: 2-4 sentences justifying the
score, calling out the single riskiest technical assumption.

Return exactly 3 objects matching the schema. No commentary.
```
