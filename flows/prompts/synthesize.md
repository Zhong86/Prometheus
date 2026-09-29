# Node: synthesize

Not a plain Prompt Template + Language Model pair — use the
**StructuredOutput** component (category: LLM Operations), which does the
LLM call and schema-validated parsing in one node.

- **Input Message** (`input_value`) ← a Prompt Template's rendered output:
  topic + negative_context + both researcher agents' findings, wired as
  `{topic}`, `{negative_context}`, `{academic_findings}`,
  `{friction_findings}`. Wire the **Academic Researcher** and **Friction
  Researcher** agents' `Response` outputs (Message-typed) into the last two
  — no Parser needed, they're already the right type.
- **Language Model** (`model`) — pick Gemini via the inline dropdown.
- **Format Instructions** (`system_prompt`) — the actual reasoning task
  lives here, not just formatting rules (see below).
- **Output Schema** (`output_schema`) — a table with three rows:
  `problem_statement` (string), `domain` (string), `target_user` (string) —
  matches `SynthesizedProblem` in `backend/app/models/idea.py`.
- **Schema Name** — `SynthesizedProblem`.

Output: `Structured Output` (JSON) with those three fields, ready to feed
the Competitor Researcher agent (via a Parser, since JSON → Message still
needs the same bridge used for AstraDB).

## Prompt Template content (feeds `input_value`)

```
Topic: {topic}

Ideas to avoid (from prior runs — steer away from these):
{negative_context}

Academic problems found:
{academic_findings}

Public friction / complaints found:
{friction_findings}
```

## Format Instructions (feeds `system_prompt`)

```
You are a startup ideation analyst. You will be given a topic, a list of
academic problems, and a list of real-world friction points found
separately — they were not pre-matched to each other.

Your job: actively decide how to combine them. Read through both lists,
judge which academic problem (if any) and which friction point (if any)
actually reinforce the same underlying issue, and fuse those into ONE
concrete, specific gap solvable by building a software product (web app,
SaaS, mobile app, API, etc.) — not a hardware, policy, or purely
operational fix. Don't just concatenate the first item from each list —
weigh relevance and pick (or synthesize across) whichever pairing produces
the most specific, coherent idea. If nothing pairs well, it's fine to build
the idea from the single strongest finding alone rather than forcing a weak
combination.

The gap must be narrow enough to name a single target user and a single
broken workflow — not a category of problems. Example of the right level
of specificity: "Manual PDF data re-keying in private clinic intake
forms" — not "healthcare data entry is hard."

Do not propose anything matching the ideas-to-avoid list, even loosely.

Return the result as valid JSON matching the provided schema —
problem_statement, domain, and target_user. No extra commentary or
markdown.
```
