"""Backend configuration, read from environment with safe defaults.

Keep secrets out of code: set these via the shell / .env / container env.
"""
import os
from pathlib import Path

from crawler.utils.backend_connection import get_backend_ingest_token

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# SQLite for local dev, override with DB_URL=postgresql+psycopg://... for prod.
DATABASE_URL = os.environ.get(
    "DB_URL", f"sqlite:///{(PROJECT_ROOT / 'data' / 'backend.db').as_posix()}"
)

# Shared token the crawler presents when calling POST /api/ingest/*.
INGEST_TOKEN = get_backend_ingest_token()

# Comma-separated allowed CORS origins (the Vue dev server, and the prod domain).
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5200").split(",")
    if o.strip()
]
