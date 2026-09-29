FROM langflowai/langflow:latest

# Athena's custom components (flows/components/athena_research) call into
# app.tools.* (SerpAPI, Tavily) — those SDKs need to be present in the
# Langflow image itself, not just the FastAPI backend's image.
RUN pip install --no-cache-dir "google-search-results>=2.4.2" "tavily-python>=0.3.3"
