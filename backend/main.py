"""FastAPI application entrypoint.

Run with:  uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .db import init_db
from .routers import ingest, policies, reports, stream

init_db()

app = FastAPI(title="STACrawler API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policies.router)
app.include_router(reports.router)
app.include_router(ingest.router)
app.include_router(stream.router)


@app.get("/health")
def health():
    return {"ok": True}
