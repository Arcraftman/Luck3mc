"""Backend API tests: report ingest + by-day / by-source listing.

Runs against a throwaway SQLite DB (overridden via DB_URL) and a fixed ingest
token, so it needs no network or real secrets. This is the contract the Vue
frontend depends on: a report carries ``date`` + ``spiders`` (comma-joined
crawler names = official websites) and can be filtered by either.
"""
import os
import tempfile

# Point the backend at a temp sqlite file BEFORE importing the app.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_URL"] = f"sqlite:///{_tmp.name}"
os.environ["BACKEND_INGEST_TOKEN"] = "test-token"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

client = TestClient(app)
TOKEN = "test-token"


def _ingest(date: str, spiders: str, title: str = "政策日报") -> int:
    r = client.post(
        "/api/ingest/report",
        headers={"X-Token": TOKEN},
        json={
            "title": f"{title} {date}",
            "content_md": f"# {date}\n内容",
            "date": date,
            "spiders": spiders,
        },
    )
    assert r.status_code == 200, r.text
    return r.status_code


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_ingest_requires_token():
    r = client.post(
        "/api/ingest/report",
        headers={"X-Token": "wrong"},
        json={"title": "x", "content_md": "y", "date": "2026-08-12", "spiders": "mof_fgk"},
    )
    assert r.status_code == 403


def test_list_and_filter_by_day_and_source():
    _ingest("2026-08-12", "mof_fgk,gov_policy_root")
    _ingest("2026-08-11", "miit_policy")

    all_r = client.get("/api/reports").json()
    assert len(all_r) == 2

    by_source = client.get("/api/reports", params={"source": "mof_fgk"}).json()
    assert [r["date"] for r in by_source] == ["2026-08-12"]

    by_day = client.get("/api/reports", params={"date": "2026-08-11"}).json()
    assert [r["spiders"] for r in by_day] == ["miit_policy"]
