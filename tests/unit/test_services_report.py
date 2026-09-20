"""Unit tests for :func:`crawler.services.report_generator.collect_items`.

Reads the committed ``data/*.jsonl`` fixtures in read-only mode — no network,
no DeepSeek, no push. Asserts the collector can surface real crawled items and
honour its ``spiders`` / ``max_items`` filters.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pytest
from crawler.services.report_generator import collect_items

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def test_report_cap_does_not_starve_later_sources(tmp_path):
    for spider, site, count in [("caishui", "tax", 40), ("gov_policy_root", "shanghai_rsj", 2)]:
        directory = tmp_path / spider
        directory.mkdir()
        rows = [{"source_site": site, "source_url": f"https://example.org/{site}/{n}",
                 "title": "政策", "pub_date": f"2026-09-{n % 17 + 1:02d}", "content": "正文"}
                for n in range(count)]
        (directory / "2026-09-17.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows + rows), encoding="utf-8")
    items = collect_items("2026-09-17", max_items=3, data_dir=tmp_path)
    assert len(items) == 5
    assert len({i["url"] for i in items}) == 5
    rsj = [i for i in items if i["source_site"] == "shanghai_rsj"]
    assert rsj and rsj[0]["pub_date"] == "2026-09-02"
    assert rsj[0]["source_name"] == "上海市人力资源和社会保障局"


def _available_dates() -> list[str]:
    files = glob.glob(str(DATA_DIR / "*" / "*.jsonl"))
    return sorted({os.path.basename(f).replace(".jsonl", "") for f in files})


@pytest.mark.skipif(
    not _available_dates(),
    reason="no data/*.jsonl fixtures present",
)
def test_collect_items_returns_entries_from_real_fixtures():
    date_str = _available_dates()[-1]  # most recent available day
    # Read the *real* committed data dir directly (read-only fixture), so the
    # test does not depend on the testing env's `storage.output_dir`.
    items = collect_items(date_str, data_dir=str(DATA_DIR))
    assert len(items) > 0
    first = items[0]
    assert set(first) >= {"spider", "title", "url", "pub_date", "authority", "content"}


@pytest.mark.skipif(
    not _available_dates(),
    reason="no data/*.jsonl fixtures present",
)
def test_collect_items_filters_by_spider():
    date_str = _available_dates()[-1]
    all_items = collect_items(date_str, data_dir=str(DATA_DIR))
    spider = all_items[0]["spider"]
    filtered = collect_items(date_str, spiders=[spider], data_dir=str(DATA_DIR))
    assert filtered
    assert all(it["spider"] == spider for it in filtered)


@pytest.mark.skipif(
    not _available_dates(),
    reason="no data/*.jsonl fixtures present",
)
def test_collect_items_respects_max_items():
    date_str = _available_dates()[-1]
    capped = collect_items(date_str, max_items=1, data_dir=str(DATA_DIR))
    from collections import Counter
    assert all(count <= 1 for count in Counter(i["source_site"] for i in capped).values())


def test_summaries_send_each_site_to_deepseek_separately(monkeypatch):
    from crawler.services import report_generator as service
    calls = []
    def fake_deepseek(items):
        calls.append(items)
        return "摘要"
    monkeypatch.setattr(service, "call_deepseek", fake_deepseek)
    items = [{"source_site": site, "source_name": site, "spider": "gov_policy_root"}
             for site in ("a", "a", "b")]
    report = service.generate_site_summaries(items)
    assert [len(c) for c in calls] == [2, 1]
    assert "## a（2 条）" in report and "## b（1 条）" in report
