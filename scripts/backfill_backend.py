#!/usr/bin/env python3
"""Import existing crawler JSONL files into the local FastAPI SQLite DB."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend import crud  # noqa: E402
from backend.db import SessionLocal, init_db  # noqa: E402
from backend.schemas import PolicyIn  # noqa: E402


def import_jsonl(data_dir: Path) -> tuple[int, int, int]:
    """Return (parsed, unique, rejected) after idempotently upserting policies."""
    parsed = rejected = 0
    by_url: dict[str, dict] = {}
    for path in sorted(data_dir.glob("*/*.jsonl")):
        for raw in path.open(encoding="utf-8", errors="replace"):
            try:
                row = json.loads(raw)
            except (TypeError, ValueError):
                rejected += 1
                continue
            parsed += 1
            url = str(row.get("source_url") or "").strip()
            title = str(row.get("title") or "").strip()
            if not url or not title:
                rejected += 1
                continue
            row["_spider"] = path.parent.name
            by_url[url] = row

    init_db()
    with SessionLocal() as session:
        for row in by_url.values():
            crud.upsert_policy(session, PolicyIn(
                title=row.get("title") or "",
                source_url=row.get("source_url") or "",
                pub_date=str(row.get("pub_date") or ""),
                pub_datetime=str(row.get("pub_datetime") or ""),
                doc_number=row.get("doc_number") or "",
                category=row.get("category") or "",
                issuing_authority=row.get("issuing_authority") or "",
                source_site=row.get("source_site") or row.get("_spider") or "",
                content=row.get("content") or "",
                subsidy=bool(row.get("subsidy", False)),
            ))
    return parsed, len(by_url), rejected


def main() -> None:
    parser = argparse.ArgumentParser(description="回填爬虫 JSONL 到 FastAPI SQLite")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data")
    args = parser.parse_args()
    parsed, unique, rejected = import_jsonl(args.data_dir)
    print(f"backend backfill complete: parsed={parsed}, unique={unique}, rejected={rejected}")


if __name__ == "__main__":
    main()
