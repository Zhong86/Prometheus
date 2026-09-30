from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.research import router as research_router

app = FastAPI(title="Athena Research API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(research_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
