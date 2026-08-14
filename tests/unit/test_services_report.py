"""Unit tests for :func:`crawler.services.report_generator.collect_items`.

Reads the committed ``data/*.jsonl`` fixtures in read-only mode — no network,
no DeepSeek, no push. Asserts the collector can surface real crawled items and
honour its ``spiders`` / ``max_items`` filters.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import pytest
from crawler.services.report_generator import collect_items

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


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
    assert len(capped) <= 1
