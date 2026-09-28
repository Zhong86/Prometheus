# Athena Research

AI-powered software idea discovery pipeline. Given a topic, Athena runs a multi-step agent pipeline — academic paper search, forum/review scraping, synthesis, competition analysis, feasibility scoring — and outputs a full PRD plus an optional HTML wireframe.

## Architecture

```
Next.js (frontend)  →  FastAPI /api/research  →  Langflow DAG
                                │
                         AstraDB (novelty filter + storage)
```

See [`athena-research-plan.md`](./athena-research-plan.md) for the full system plan.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker & Docker Compose | latest |

---

## Local Setup

### 1. Clone & configure environment

```bash
git clone <repo-url>
cd Athena_Research
cp .env.example .env
# Fill in all values in .env
```

### 2. Start Langflow (Docker)

```bash
docker compose up langflow -d
```

Open [http://localhost:7860](http://localhost:7860), import `/flows/athena_research_flow.json` (once created in Sub-Task 12), copy the **Flow ID**, and set it in `.env`:

```
LANGFLOW_FLOW_ID=<paste-flow-id-here>
```

### 3. Start the FastAPI backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Start the Next.js frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 5. (Optional) Run everything with Docker Compose

```bash
docker compose up --build
```

> The `backend` service also starts via Docker Compose. The frontend is run separately in dev mode for fast HMR.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `ASTRA_DB_TOKEN` | AstraDB application token |
| `ASTRA_DB_ENDPOINT` | AstraDB endpoint URL |
| `ASTRA_DB_KEYSPACE` | AstraDB keyspace name |
| `SERPAPI_KEY` | SerpAPI key (Google Scholar engine) |
| `TAVILY_API_KEY` | Tavily API key |
| `LANGFLOW_BASE_URL` | Langflow base URL (default: `http://localhost:7860`) |
| `LANGFLOW_FLOW_ID` | Flow ID from the Langflow UI |

---

## Project Structure

```
.
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── main.py           # App entry point + CORS
│   │   ├── routes/           # API route handlers
│   │   ├── tools/            # SerpAPI / Tavily wrappers
│   │   ├── db/               # AstraDB client utilities
│   │   ├── models/           # Pydantic schemas
│   │   └── services/         # Gemini wireframe generator
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                 # Next.js app (TypeScript + Tailwind)
│   ├── app/                  # App Router pages
│   ├── components/           # Shared React components
│   └── lib/                  # API client utilities
├── flows/                    # Langflow JSON exports & custom components
│   └── components/
├── docker-compose.yml
├── .env.example
└── athena-research-plan.md
```

---

## Sub-Task Progress

See [`athena-research-plan.md`](./athena-research-plan.md) for detailed per-sub-task status.
