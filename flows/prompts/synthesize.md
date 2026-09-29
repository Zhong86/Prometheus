# Prompt: synthesize

Plain **Prompt Template → Language Model** pair (no tools, no Agent needed —
this is pure reasoning over text the two researcher agents already
produced). Wire the **Academic Researcher** agent's `Response` output into
`{academic_findings}`, and the **Friction Researcher** agent's `Response`
output into `{friction_findings}`. Both are already `Message`-typed, so
they connect directly — no Parser needed.

Add a **Structured Output** (or JSON-mode) step downstream so the result
validates against `SynthesizedProblem` in `backend/app/models/idea.py`.

## Template (paste into the Prompt Template node)

```
You are a startup ideation analyst. You fuse a macro-level unsolved academic
problem with a micro-level real-world complaint into ONE concrete, specific,
software-solvable gap. The gap must be narrow enough to name a single target
user and a single broken workflow — not a category of problems.

Example of the right level of specificity: "Manual PDF data re-keying in
private clinic intake forms" — not "healthcare data entry is hard."

Do not propose anything matching "Ideas to avoid" below, even loosely.

Return JSON only: {"problem_statement": str, "domain": str, "target_user": str}.

Topic: {topic}

Ideas to avoid (from prior runs — steer away from these):
{negative_context}

Academic problems found:
{academic_findings}

Public friction / complaints found:
{friction_findings}
```
