# Node: spec_generator (Structured Output → IdeaPayload)

No custom Python component — use Langflow's built-in **Structured Output**
component (Prompt Template → Google Generative AI Model → Structured Output)
configured with the schema below. It must produce the same shape as
`IdeaPayload` in `backend/app/models/idea.py`, since this is the JSON payload
written to AstraDB and returned to the frontend.

## Structured Output schema (paste field-by-field into the component's schema table)

| Field | Type | Notes |
|---|---|---|
| `niche` | string | Short name for the idea, e.g. "Clinic Intake OCR" |
| `problem_statement` | string | From `synthesize` |
| `target_user` | string | From `synthesize` |
| `feasibility_score` | integer (1-10) | From `feasibility.solvability_score` |
| `proof_of_pain_url` | string | Best supporting URL from `public_friction` |
| `tech_stack` | list[string] | Derived from `feasibility.required_apis` + reasoning |
| `competitors` | list[object: name, pricing, gaps] | From `competition_analyst` |
| `market_gap_summary` | string | From `competition_analyst` |

## System prompt for the model feeding the Structured Output component

You are compiling a final structured record for a validated software idea.
Combine the upstream synthesis, feasibility, and competitor data into one
object matching the schema exactly. Pick the single most compelling
`proof_of_pain_url` from the public friction results — prefer a direct
review/forum link over a generic homepage. Derive `tech_stack` as a short
list of concrete technologies (e.g. "FastAPI", "Tesseract OCR",
"Next.js") implied by `required_apis` and `reasoning`, not a restatement of
this pipeline's own stack.

## User

Niche seed: {problem_statement}
{target_user}

Feasibility: {feasibility_assessment}
Public friction sources: {public_friction}
Competitors + market gap: {competition_analysis}
