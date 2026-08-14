"""Backend configuration, read from environment with safe defaults.

Keep secrets out of code: set these via the shell / .env / container env.
"""
import os

# SQLite for local dev, override with DB_URL=postgresql+psycopg://... for prod.
DATABASE_URL = os.environ.get("DB_URL", "sqlite:///./data/backend.db")

# Shared token the crawler presents when calling POST /api/ingest/*.
INGEST_TOKEN = os.environ.get("BACKEND_INGEST_TOKEN", "change-me-ingest-token")

# Comma-separated allowed CORS origins (the Vue dev server, and the prod domain).
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5200").split(",")
    if o.strip()
]
