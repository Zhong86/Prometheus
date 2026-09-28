# Langflow flows

This directory holds everything Langflow-side: custom components that wrap
external APIs, and reference prompt templates for the pure-Gemini reasoning
steps that use Langflow's *built-in* Prompt + Model + Structured Output
components instead of custom Python.

## Layout

```
flows/
├── components/
│   └── athena_research/       # LANGFLOW_COMPONENTS_PATH category folder
│       ├── _bootstrap.py      # puts backend/ on sys.path
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

## Running it

This repo doesn't run Langflow itself — point your own instance (local
`pip install`, desktop app, whatever) at this folder. The backend only ever
talks to it over HTTP via `LANGFLOW_BASE_URL`, so it doesn't matter how or
where Langflow is hosted.

```bash
pip install google-search-results tavily-python   # into Langflow's own env
export LANGFLOW_COMPONENTS_PATH=/absolute/path/to/Athena_Research/flows/components
export SERPAPI_KEY=...      # so components can fall back to env vars
export TAVILY_API_KEY=...
langflow run
```

On startup Langflow should list **Academic Problems (SerpAPI Scholar)**,
**Public Friction (Tavily)**, and **Competition Analyst (Tavily)** in the
component sidebar (search "Athena" or look under a custom category).
`_bootstrap.py` finds `backend/` by walking up from its own file path, so
this works as long as `flows/` and `backend/` stay siblings on disk — no
extra path config needed beyond `LANGFLOW_COMPONENTS_PATH`.

Each component also has a `SecretStrInput` for its API key if you'd rather
set it per-node in the UI instead of via environment variables.

## What's still manual (Sub-Task 12)

Assembling the full DAG — dragging these components onto the canvas,
wiring them to built-in Prompt/Model/Structured Output nodes using the
templates in `prompts/`, connecting `negative_context` from the (still
to-be-built, Sub-Task 2) AstraDB pre-search into every relevant node, and
exporting the result to `athena_research_flow.json` — has to happen in your
Langflow instance's UI, since that's where node IDs/positions/edges get
generated. Once wired, export the flow and copy its Flow ID into `.env` as
`LANGFLOW_FLOW_ID` (and set `LANGFLOW_BASE_URL` if it's not the default
`http://localhost:7860`).
