# Node: synthesize (LLM call 2 of 4)

**Structured Output** component (category: LLM Operations). Turns the
academic papers and user complaints into **3 distinct ideas** a developer
could build, and — because it now knows each problem, user and the tools
they complain about — also writes each idea's competitor search queries.

Structured Output natively returns a list of objects; with more than one it
emits `{"results": [ {...}, {...}, {...} ]}`. Every downstream node
(Competition Analyst, Format Ideas, Idea Report) handles that shape.

- **Input Message** (`input_value`) ← Prompt Template below.
- **Language Model** — Google Generative AI, `gemini-3.5-flash-lite`.
  If ideas come out vague, move just this node to `gemini-3.5-flash`.
- **Format Instructions** (`system_prompt`) ← text below.
- **Schema Name** — `SynthesizedProblem`.
- **Output Schema** — see table. `problem_statement`, `domain` and
  `target_user` match `SynthesizedProblem` in `backend/app/models/idea.py`.
- **Output** (`structured_output`, JSON) →
  - `queries` on **Competition Analyst** (key `competitor_queries`)
  - **Format Ideas** (header/template below) → Competition Analysis and
    Feasibility prompt templates as `{idea}`
  - `synthesis` on **Idea Report**

## Output Schema

Field order matters: the model fills fields in schema order, so `evidence`
comes before `problem_statement` to make it ground each idea in specific
findings before naming it. `evidence` is a list of pipe-separated strings
rather than `dict` because Gemini returns empty `{}` objects for free-form
`dict` fields; **Idea Report** parses them into `{source, finding, url}`.

| Name | Type | As List | Description |
|---|---|---|---|
| `idea_id` | int | False | 1, 2 or 3. |
| `evidence` | str | True | 2-4 findings this idea is built on, formatted exactly as: `source \| finding in one sentence \| url`, where source is one of paper, reddit, hackernews, capterra, producthunt. From at least two different sources whenever possible. Copy URLs exactly from the input. |
| `problem_statement` | str | False | One concrete sentence naming the specific broken workflow and who has it, e.g. "Manual PDF data re-keying in private clinic intake forms." |
| `niche` | str | False | Short product-style title for the idea, 2-5 words, e.g. "Clinic Intake PDF Extractor". Names the product, not the company; no marketing words. |
| `domain` | str | False | Industry or category, e.g. "Healthcare", "Legal", "DevOps", "Agriculture". |
| `target_user` | str | False | The specific role that has this problem, e.g. "Solo clinic administrative staff". |
| `solution_type` | str | False | Exactly one of: software, ai_automation, iot, other_tech. |
| `solution_approach` | str | False | 1-2 sentences on what a developer would build, e.g. "A web app that runs uploaded intake PDFs through an OCR + LLM extraction pipeline and pushes fields into the clinic's PMS via its API." |
| `competitor_queries` | str | True | 2 short web search queries to find existing products or open-source projects that already tackle this problem. |

## Prompt Template (feeds `input_value`)

```
Topic: {topic}

Ideas to avoid (from prior runs — steer away from these):
{negative_context}

Academic papers found:
{academic_findings}

Public friction / complaints found (grouped by site):
{friction_findings}
```

- `{topic}` ← Chat Input.
- `{negative_context}` ← Astra DB search → Parser.
- `{academic_findings}` ← Academic Problems `papers`.
- `{friction_findings}` ← Public Friction `complaints`.

## Format Ideas template (Structured Output → `{idea}` downstream)

Header:

```
===== Idea {idea_id}: {niche} =====
```

Template:

```
Problem statement: {problem_statement}
Domain: {domain}
Target user: {target_user}
Solution type: {solution_type}
Proposed solution: {solution_approach}
```

## Format Instructions (feeds `system_prompt`)

```
You are a startup ideation analyst working for a software developer who
wants to find real problems to build products for. You are given a topic, a
list of academic papers, and real-world user complaints from Reddit, Hacker
News, Capterra and Product Hunt, grouped into blocks headed
"===== Source: <site> =====". The papers and complaints were found
separately and were not pre-matched. Some results are irrelevant noise —
ignore those, including papers from unrelated fields.

Return exactly 3 objects — 3 different ideas, with idea_id 1, 2 and 3.

1. Read every source. Go through the papers and every source block before
deciding anything; don't stop after the first block. Treat Capterra reviews
as strong evidence: they are users complaining about the software
they already pay for, which is exactly where a developer can build
something better.

2. Pick 3 distinct problems. Each idea must address a different underlying
problem — a different broken workflow, or a different target user — not
three variations or feature sets of the same idea. Rank them: idea 1 is the
best-supported problem. Prefer problems that show up in more than one
source (e.g. a Reddit complaint confirmed by Capterra reviews, or a
complaint backed by a paper) over a one-off comment, and don't pick a
problem just because its source had the most results.

Each idea must be something a developer or small dev team (1-3 people)
could solve with technology:
- software: web/mobile/desktop app, SaaS, API, integration, browser
  extension, developer tool
- ai_automation: LLM agent or workflow, ML model, scripted automation
- iot: sensors or embedded devices with software, built from off-the-shelf
  hardware
- other_tech: anything else achievable mainly through code
Not a policy, legal, staffing or purely operational fix, and not something
that needs custom hardware manufacturing, regulatory approval (e.g. a
medical device) or a large enterprise sales cycle before anyone can use it.

Each problem must be narrow enough to name a single target user and a
single broken workflow — not a category of problems. Right level of
specificity: "Manual PDF data re-keying in private clinic intake forms".
Too broad: "healthcare data entry is hard".

Do not propose anything matching the ideas-to-avoid list, even loosely.

3. For each idea, fill in this order:
- evidence: 2-4 findings the idea is built on, as "source | finding |
  url", from at least two different sources whenever the research allows.
  The same finding may support more than one idea only if nothing else
  fits. Never invent URLs.
- problem_statement, then niche: a short 2-5 word product-style title
  for the idea (e.g. "Clinic Intake PDF Extractor"), then domain and
  target_user.
- solution_type, and in solution_approach 1-2 sentences on what the
  developer would build and its key technical pieces (which data it reads,
  which model or device it uses, which system it integrates with).
- competitor_queries: exactly 2 short web search queries that would
  surface existing products already tackling this problem:
  1. commercial products — the product category plus the user ("clinic
     intake form automation software"), or "alternatives to <tool>" when
     the complaints name the tool the user is stuck with;
  2. open-source projects — "<task> open source github".
  Plain text, no quotes or operators, never the full problem_statement
  sentence.

Return exactly 3 objects matching the schema. No commentary.
```
