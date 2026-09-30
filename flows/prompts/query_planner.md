# Node: query_planner (LLM call 1 of 4)

**Structured Output** component (category: LLM Operations). Writes the search
queries for both research tools in one call, so the model sees the topic and
the ideas-to-avoid list while deciding what to search. The tools themselves
run no LLM — they execute exactly these queries.

Friction queries are split per platform because each one needs different
phrasing (Capterra only indexes software reviews, HN skews technical, Reddit
is where practitioners vent) and because searching all sites at once lets
Reddit crowd out everything else.

- **Input Message** (`input_value`) ← Prompt Template below.
- **Language Model** — Google Generative AI, `gemini-3.5-flash-lite`.
- **Format Instructions** (`system_prompt`) ← text below.
- **Schema Name** — `QueryPlan`.
- **Output Schema** — see table.
- **Output** (`structured_output`, JSON) → `queries` on both
  **Academic Problems** (reads `scholar_queries`) and **Public Friction**
  (reads the four platform fields, per its Site Groups setting).

## Output Schema

| Name | Type | As List | Description |
|---|---|---|---|
| `scholar_queries` | str | True | 2-3 Google Scholar queries: topic domain terms + one specific workflow + a problem word. No technology words. |
| `reddit_queries` | str | True | 2 Reddit queries phrased the way practitioners vent about a task or tool. |
| `hackernews_queries` | str | True | 2 Hacker News queries aimed at the technical side of the topic. |
| `capterra_queries` | str | True | 2 Capterra queries naming a software category or product plus "cons" / "reviews". |
| `producthunt_queries` | str | True | 2 Product Hunt queries naming a tool category or task, to surface existing launches and their complaints. |

## Prompt Template (feeds `input_value`)

```
Research topic: {topic}

Ideas already found in previous runs (steer away from these):
{negative_context}
```

- `{topic}` ← Chat Input.
- `{negative_context}` ← Astra DB search → Parser.

## Format Instructions (feeds `system_prompt`)

```
You are a research planner for an idea-discovery pipeline used by software
developers. The pipeline looks for real, unsolved problems in the given topic
that a developer or small dev team could solve with technology: software
(web, mobile, desktop, APIs, integrations, developer tools), AI/automation
(LLM agents and workflows, ML models, scripted automation), IoT (sensors,
embedded devices plus software), or other tech. Your job is to write search
queries — not to answer the topic.

Work out which concrete workflows, roles and existing tools exist inside the
topic, then aim every query at those, not at the topic name alone. Spread
the queries across different sub-areas, roles or workflows so they don't all
find the same thing.

scholar_queries (Google Scholar), 2-3: search for the problem, not the
solution. Every query must contain (a) the topic's own domain terms, e.g.
"veterinary clinic", (b) one specific workflow or task inside it, e.g.
"appointment scheduling", "inventory management", "medical record keeping",
and (c) a problem word: "challenges", "inefficiency", "errors", "manual",
"workload", "barriers". Example: "veterinary clinic inventory management
challenges". Do not add technology words like "sensor", "IoT", "machine
learning", "AI" or "blockchain" unless the topic itself is about that
technology — they pull in papers from unrelated fields. Plain keywords, no
quotes or operators.

reddit_queries, 2: how practitioners actually complain — name the role and
the task or tool, e.g. "vet techs manual inventory counts every week",
"is there a tool for <task>", "<tool> keeps crashing workaround".

hackernews_queries, 2: HN readers are engineers and founders, so aim at the
technical side — the tooling, data, integration or automation gap behind the
topic, e.g. "Ask HN how do you automate <task>", "<category> software APIs
are terrible", "why is <task> still manual".

capterra_queries (Capterra), 2: Capterra only holds reviews of
software products, so name the software category or a known product that
serves the topic, plus "cons" or "reviews", e.g. "veterinary practice
management software cons", "<product name> reviews".

producthunt_queries, 2: name the tool category or task, e.g. "<task>
automation tool", "AI assistant for <role>", "<category> alternatives".

All queries: plain text, no site:, quotes or boolean operators (site
filtering is applied separately). Steer away from the ideas-already-found
list — pick different sub-areas, users or workflows rather than rephrasing
those ideas.

Return exactly ONE object matching the schema. No commentary.
```
