# Athena Research — System Plan

## Top-Level Overview

Athena Research is a local-only AI pipeline that helps a user discover **novel, buildable software ideas** from a given topic. It combines academic problem discovery (macro) with real-world user friction (micro), synthesizes a unique gap, validates it against the market and technical reality, generates a full PRD artifact, and optionally produces a Gemini-generated HTML/Tailwind wireframe.

**Core stack:**

* **Langflow** — primary orchestration layer (agent nodes, prompt chains, structured outputs)
* **FastAPI (Python)** — backend API that triggers the Langflow flow via its REST API, handles AstraDB reads/writes, and serves the frontend
* **Next.js** — frontend UI for topic input, results display, and wireframe preview
* **AstraDB** — vector database for storing discovered ideas and driving the novelty filter
* **Gemini** — LLM for all reasoning, synthesis, and wireframe generation nodes
* **SerpAPI** (`google_scholar` engine) — academic paper search
* **Tavily** — web search, forum scraping, and raw content extraction (Capterra, G2, Reddit, Trustpilot)

**Key design principle:** AstraDB is queried at the start of every run. The semantically similar ideas already stored are passed as negative context ("avoid these") into every agent that generates new content.

---

## Architecture Summary

```
User Topic Input (Next.js)
  │
  ▼
FastAPI /research endpoint
  │
  ├─ 1. AstraDB Pre-Search (novelty filter — fetch similar stored ideas)
  │
  ├─ 2a. academic_problems   ──┐
  │      (SerpAPI Scholar)     ├─ parallel (Langflow DAG)
  ├─ 2b. public_friction     ──┘
  │      (Tavily Advanced Search)
  │
  ├─ 3. synthesize (Langflow prompt chain — Gemini)
  │
  ├─ 4. competition_analyst (Tavily — Gemini)
  │
  ├─ 5. Technical Feasibility Evaluator (Langflow agent — Gemini)
  │
  ├─ 6. Dual Spec & Artifact Generator (Langflow structured output — Pydantic)
  │       ├─ JSON payload (for AstraDB write)
  │       └─ Markdown PRD file
  │
  ├─ 7. [Optional] HTML Wireframe (Gemini prompt → single-file HTML+Tailwind)
  │
  └─ 8. AstraDB Write (store idea embedding + JSON payload)

```

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold & Environment Setup

**Intent:** Establish the monorepo structure, dependency files, and environment variable configuration so all subsequent sub-tasks have a stable foundation to build on.

**Expected Outcomes:**

* `/backend` Python FastAPI project initialised with `pyproject.toml` or `requirements.txt`
* `/frontend` Next.js project scaffolded
* `.env.example` listing all required secrets
* `docker-compose.yml` for running Langflow locally alongside the FastAPI server
* README with local setup instructions

**Todo List:**

1. Create monorepo root with `/backend`, `/frontend`, `/flows` (Langflow JSON exports) directories
2. Scaffold FastAPI app in `/backend` with a single health-check route
3. Scaffold Next.js app in `/frontend` (TypeScript, Tailwind CSS)
4. Create `.env.example` with keys: `GEMINI_API_KEY`, `ASTRA_DB_TOKEN`, `ASTRA_DB_ENDPOINT`, `ASTRA_DB_KEYSPACE`, `SERPAPI_KEY`, `TAVILY_API_KEY`, `LANGFLOW_BASE_URL`, `LANGFLOW_FLOW_ID`
5. Add `docker-compose.yml` for Langflow service (`langflowai/langflow:latest`)
6. Write root `README.md` with setup steps

**Status:** `[x] done`

---

### Sub-Task 2 — AstraDB Schema & Novelty Filter

**Intent:** Define the AstraDB collection schema for stored ideas and implement the pre-search novelty filter that retrieves semantically similar past ideas to feed as negative context into the pipeline.

**Expected Outcomes:**

* AstraDB collection `athena_ideas` created with vector indexing on the `embedding` field
* FastAPI utility function `get_similar_ideas(topic: str, top_k: int) -> list[dict]` that embeds the topic with Gemini embeddings and queries AstraDB
* FastAPI utility function `write_idea(payload: dict, embedding: list[float])` that stores a completed idea
* The similar ideas returned are formatted as a `negative_context` string: a bulleted list of previously found idea titles/niches to avoid

**Todo List:**

1. Create AstraDB collection `athena_ideas` with fields: `id`, `niche`, `problem_statement`, `feasibility_score`, `proof_of_pain_url`, `tech_stack`, `prd_markdown`, `embedding` (`models/text-embedding-004`)
2. Implement `/backend/app/db/astra.py` with `get_similar_ideas` and `write_idea` functions using `astrapy`
3. Implement `embed_text(text: str) -> list[float]` using Gemini's embedding API
4. Write unit test (local, no mock) that inserts a dummy idea and retrieves it

**Status:** `[ ] pending`

---

### Sub-Task 3 — Langflow Flow: academic_problems Node

**Intent:** Build the Langflow node (and its backing Python tool) that uses SerpAPI with `engine=google_scholar` to find unsolved academic problems related to the user's topic.

**Expected Outcomes:**

* A working Langflow component/tool node `academic_problems` callable via the flow
* Accepts: `topic`, `domain_filters`, `negative_context`
* Returns: list of `{title, abstract, citation_summary, problem_statement}` objects
* SerpAPI call uses `engine=google_scholar`, filters to recent papers, and injects `negative_context` keywords as exclusions

**Todo List:**

1. Create `/backend/app/tools/academic_problems.py` wrapping SerpAPI `google_scholar` engine
2. Register it as a Langflow custom component in `/flows/components/academic_problems.py`
3. Prompt engineering: system prompt instructs Gemini to extract unsolved problem statements from paper abstracts, explicitly avoiding topics matching `negative_context`
4. Export/save Langflow node configuration to `/flows/academic_problems_node.json`

**Status:** `[ ] pending`

---

### Sub-Task 4 — Langflow Flow: public_friction Node

**Intent:** Build the Langflow node that uses Tavily advanced search to surface raw micro-level user pain points from forums and review sites.

**Expected Outcomes:**

* A working Langflow component `public_friction`
* Accepts: `topic`, `negative_context`
* Tavily call uses `search_depth="advanced"` and `include_raw_content=True` with site-targeted queries (Capterra, G2, Reddit, Trustpilot)
* Returns: list of raw complaint/review quotes with source URLs

**Todo List:**

1. Create `/backend/app/tools/public_friction.py` wrapping the Tavily Python SDK
2. Build site-operator query strings (e.g. `site:capterra.com "{topic}" clunky OR "doesn't work"`) combined with negative DB keywords from `negative_context`
3. Register as a Langflow custom component in `/flows/components/public_friction.py`
4. Export node config to `/flows/public_friction_node.json`

**Status:** `[ ] pending`

---

### Sub-Task 5 — Langflow Flow: synthesize Node

**Intent:** Build the Langflow prompt-chain node that combines academic abstracts and raw forum complaints into a single, specific, software-solvable problem statement.

**Expected Outcomes:**

* Langflow `synthesize` node wired to receive outputs from both `academic_problems` and `public_friction`
* Gemini prompt that fuses macro + micro findings into one concrete gap statement (e.g., *"Manual PDF data re-keying in private clinic intake forms"*)
* Output is a single structured object: `{problem_statement: str, domain: str, target_user: str}`

**Todo List:**

1. Design the Gemini system prompt for synthesis — must reference `negative_context` to steer away from known ideas
2. Create Langflow Prompt node wired to Gemini model component
3. Add output parser (Pydantic or JSON mode) to enforce structured output
4. Export node config to `/flows/synthesize_node.json`

**Status:** `[ ] pending`

---

### Sub-Task 6 — Langflow Flow: competition_analyst Node

**Intent:** Build the node that takes the synthesized problem statement and uses Tavily to find existing SaaS competitors, documenting their pricing and feature gaps.

**Expected Outcomes:**

* Langflow `competition_analyst` node
* Uses Tavily to search for existing products solving the problem
* Gemini analyses results and extracts: competitor name, pricing model, missing features, poor integrations, UX complaints
* Output: `{competitors: [{name, pricing, gaps}], market_gap_summary: str}`

**Todo List:**

1. Create `/backend/app/tools/competition_analyst.py` using Tavily search
2. Design Gemini prompt to act as a market analyst — focus on feature gaps and weaknesses
3. Register as a Langflow component and wire after `synthesize`
4. Export node config to `/flows/competition_analyst_node.json`

**Status:** `[ ] pending`

---

### Sub-Task 7 — Langflow Flow: Technical Feasibility Evaluator Node

**Intent:** Build the node that scores how buildable the idea is, identifies required APIs, and estimates MVP complexity.

**Expected Outcomes:**

* Langflow `feasibility` node accepting synthesized problem + competitor gap list
* Outputs: `{solvability_score: int (1-10), required_apis: [str], mvp_complexity: "low|medium|high", reasoning: str}`
* Gemini reasons about API availability, data complexity, and integration burden

**Todo List:**

1. Design Gemini prompt as a technical architect evaluator
2. Include lightweight API checks via Tavily to verify endpoint existence if needed
3. Register as a Langflow component and wire after `competition_analyst`
4. Export node config to `/flows/feasibility_node.json`

**Status:** `[ ] pending`

---

### Sub-Task 8 — Langflow Flow: Dual Spec & Artifact Generator Node

**Intent:** Build the final generation node that produces both a machine-readable JSON payload and a human-readable Markdown PRD from all upstream data.

**Expected Outcomes:**

* Langflow structured output node using Pydantic schema
* **JSON payload** fields: `niche`, `problem_statement`, `target_user`, `feasibility_score`, `proof_of_pain_url`, `tech_stack`, `competitors`, `market_gap_summary`
* **Markdown PRD** sections: Problem Statement, User Stories, Proposed Tech Stack, API Endpoints, Competitor Analysis, Feasibility Notes
* Both artifacts returned to FastAPI

**Todo List:**

1. Define Pydantic schema `IdeaPayload` in `/backend/app/models/idea.py`
2. Build Langflow Structured Output node with `IdeaPayload` schema
3. Build second Langflow Prompt node that generates the Markdown PRD from the same upstream data
4. Wire outputs to flow output nodes
5. Export node config to `/flows/spec_generator_node.json`

**Status:** `[ ] pending`

---

### Sub-Task 9 — Direct Gemini Call: HTML Wireframe Generator (Optional Downstream)

**Intent:** Build an optional downstream handler in FastAPI that uses a direct Gemini API call to generate a single-file HTML+Tailwind wireframe for the proposed product when requested by the user.

**Expected Outcomes:**

* Direct Gemini prompt takes the Markdown PRD + problem statement and generates a single-file `index.html` using Tailwind CDN
* Decoupled from the primary Langflow graph execution
* Output is the raw HTML string returned to the frontend for preview inside an iframe

**Todo List:**

1. Design Gemini system prompt for HTML wireframe generation (Tailwind CDN, interactive tabs/modals via Alpine.js)
2. Add FastAPI helper function `generate_html_wireframe(prd_text: str)` in `/backend/app/services/wireframe.py`
3. Trigger conditionally based on user choice

**Status:** `[ ] pending`

---

### Sub-Task 10 — FastAPI Backend: Orchestration Layer

**Intent:** Build the FastAPI `/research` endpoint that orchestrates the execution flow: runs the novelty filter, triggers the Langflow REST API, collects artifacts, writes to AstraDB, and returns results to the frontend.

**Expected Outcomes:**

* `POST /api/research` accepts `{topic: str, domain_filters: list[str], generate_wireframe: bool}`
* Runs AstraDB pre-search $\rightarrow$ formats `negative_context`
* Triggers single Langflow execution call (`POST /api/v1/run/{flow_id}`) passing `topic` and `negative_context` via `tweaks`
* Collects JSON payload and Markdown PRD
* Option to trigger Sub-Task 9 HTML Wireframe if requested
* Writes final idea to AstraDB
* Returns complete result object to frontend
* `GET /api/ideas` returns list of all stored ideas from AstraDB

**Todo List:**

1. Implement `/backend/app/routes/research.py` with orchestration logic
2. Use `httpx.AsyncClient` to call Langflow REST API (`POST http://localhost:7860/api/v1/run/{flow_id}`)
3. Implement `/backend/app/routes/ideas.py` for listing stored ideas
4. Wire all routes into FastAPI app in `/backend/app/main.py`
5. Add CORS middleware permitting Next.js dev server origin

**Status:** `[ ] pending`

---

### Sub-Task 11 — Next.js Frontend

**Intent:** Build the Next.js frontend: topic input form, results display showing the PRD and competitor analysis, optional wireframe preview iframe, and a sidebar listing past ideas from AstraDB.

**Expected Outcomes:**

* Topic input form with domain filter tags and a "Generate Wireframe" toggle
* Results page showing problem statement, feasibility score, competitor table, rendered Markdown PRD, and optional HTML wireframe iframe
* Sidebar/history panel listing past ideas fetched from `GET /api/ideas`

**Todo List:**

1. Create `/frontend/app/page.tsx` — topic input form
2. Create `/frontend/app/results/page.tsx` — results display
3. Create `/frontend/components/IdeaCard.tsx` — card for past ideas sidebar
4. Implement API client in `/frontend/lib/api.ts` calling FastAPI endpoints
5. Render Markdown PRD using `react-markdown`
6. Render HTML wireframe in a sandboxed `<iframe srcDoc={html} />`

**Status:** `[ ] pending`

---

### Sub-Task 12 — Langflow Flow Assembly & End-to-End Test

**Intent:** Wire all individual Langflow nodes into a single complete flow, export it as a JSON file, and validate the full pipeline end-to-end with a real topic input.

**Expected Outcomes:**

* Single Langflow flow JSON at `/flows/athena_research_flow.json` containing all nodes wired in correct DAG order
* Full pipeline runs locally without errors given a test topic
* AstraDB receives the written idea after the run
* Frontend displays results correctly

**Todo List:**

1. Open Langflow UI, import all individual node configs, and wire them into one flow
2. Set all Gemini model components to use `GEMINI_API_KEY` from environment
3. Export complete flow to `/flows/athena_research_flow.json`
4. Record `flow_id` and add to `.env.example`
5. Run full end-to-end test with topic "healthcare intake forms"
6. Verify AstraDB write and verify that a second run on the same topic steers away from the first result

**Status:** `[ ] pending`