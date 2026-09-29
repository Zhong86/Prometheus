# Langflow flows

This directory holds everything Langflow-side: custom components that wrap
external APIs, and reference prompt templates for the pure-Gemini reasoning
steps that use Langflow's *built-in* Prompt + Model + Structured Output
components instead of custom Python.

## Layout

```
flows/
├── Dockerfile                 # langflowai/langflow + google-search-results + tavily-python
├── components/
│   └── athena_research/       # LANGFLOW_COMPONENTS_PATH category folder
│       ├── academic_problems.py
│       ├── public_friction.py
│       └── competition_analyst.py
└── prompts/                   # paste these into Langflow's Prompt Template component
    ├── academic_problem_extraction.md
    ├── synthesize.md
    ├── competition_analyst.md
    ├── feasibility.md
    ├── spec_generator_prd.md
    └── spec_generator_json.md
```

## Why only 3 nodes are custom Python

Langflow already ships a Prompt Template component and a Google Generative
AI model component. Any node that's *pure reasoning* (synthesize,
feasibility, spec_generator) is built from those two, wired together in the
UI, using the prompt text in `prompts/`. Custom Python is reserved for the
three nodes that talk to an external API Langflow doesn't already wrap:
SerpAPI (`academic_problems`) and Tavily (`public_friction`,
`competition_analyst`).

Each custom component returns **raw** search results (titles, abstracts,
quotes, URLs) — not LLM-extracted fields. The corresponding prompt file
takes it from there. This keeps the API-calling code out of prompt strings
and the prompt text out of Python, so either can change independently.

Each component is fully self-contained (SerpAPI/Tavily calls inlined
directly, no imports from `backend/`) — Langflow loads component files
through its own bundle-module mechanism rather than a normal Python package
import, so a `sys.path` bridge to `backend/app/tools/*` doesn't reliably
work at runtime. The same search logic also exists in
`backend/app/tools/*.py` for the FastAPI side; the two copies are
intentionally separate runtime environments, so keep them in sync by hand if
the query-building logic changes.

## Running it

```bash
cp .env.example .env   # fill in GEMINI_API_KEY, SERPAPI_KEY, TAVILY_API_KEY at minimum
docker compose up langflow -d
```

The `langflow` service builds from `flows/Dockerfile` (stock Langflow image
+ the two search SDKs), mounts the whole repo read-only at
`/app/project`, and starts Langflow with
`--components-path /app/project/flows/components` (the CLI flag, not the
`LANGFLOW_COMPONENTS_PATH` env var — that env var has a known reliability
issue on recent Langflow versions). On startup Langflow should list
**Academic Problems (SerpAPI Scholar)**, **Public Friction (Tavily)**, and
**Competition Analyst (Tavily)** in the component sidebar (search "Athena"
or look under a custom category).

Each component has a `SecretStrInput` for its API key, but leaving it blank
falls back to `SERPAPI_KEY`/`TAVILY_API_KEY` from the environment (i.e. your
`.env`), since `env_file: .env` is wired into the `langflow` service too.

## What's still manual (Sub-Task 12)

Assembling the full DAG — dragging these components onto the canvas,
wiring them to built-in Prompt/Model/Structured Output nodes using the
templates in `prompts/`, connecting `negative_context` from the (still
to-be-built, Sub-Task 2) AstraDB pre-search into every relevant node, and
exporting the result to `athena_research_flow.json` — has to happen in the
Langflow UI at http://localhost:7860, since that's where node IDs/positions/
edges get generated. Once wired, export the flow and copy its Flow ID into
`.env` as `LANGFLOW_FLOW_ID`.
