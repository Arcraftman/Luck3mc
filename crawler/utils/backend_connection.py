"""Shared local-backend connection settings without committing secrets."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOKEN_FILE = PROJECT_ROOT / "data" / "backend-ingest-token"


def get_backend_ingest_token() -> str:
    """Return the env token or a persistent, owner-only local token."""
    configured = os.environ.get("BACKEND_INGEST_TOKEN", "").strip()
    if configured:
        return configured
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(48)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(token + "\n")
    return token
