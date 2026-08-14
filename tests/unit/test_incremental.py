"""Unit tests for the incremental / watermark helper."""

from crawler.utils.incremental import WatermarkStore, _as_date


def test_as_date_normalises_iso_only():
    assert _as_date("2026-08-11") == "2026-08-11"
    assert _as_date("2026-08-11T10:30:00") == "2026-08-11"
    assert _as_date(None) is None
    # Chinese-format dates are NOT ISO; the watermark expects normalised dates.
    assert _as_date("2026年08月11日") is None


def test_watermark_should_crawl(tmp_path):
    store = WatermarkStore(tmp_path)
    # No watermark yet -> everything is new.
    assert store.should_crawl("caishui", "2026-08-01") is True

    store.update("caishui", "2026-08-10")
    assert store.should_crawl("caishui", "2026-08-09") is False  # older
    assert store.should_crawl("caishui", "2026-08-10") is False  # equal, not newer
    assert store.should_crawl("caishui", "2026-08-11") is True   # newer

    # Unknown / unparseable dates are always kept (never silently dropped).
    assert store.should_crawl("caishui", None) is True
