"""Incremental / watermark crawling support (framework-level, site-agnostic).

Government tax portals publish continuously. Re-crawling everything every run
is wasteful and re-ingests duplicates. A *watermark* records the newest
``pub_date`` seen on the previous successful run; on the next run we skip items
that are not strictly newer than the watermark, so only genuinely new items are
stored.

The store is file-backed by default (``data/watermarks/<spider>.json``) which
needs no external service; a database-backed variant can be dropped in later
for shared state across machines.
"""

import json
from datetime import date, datetime
from pathlib import Path

from crawler.utils.log_config import get_logger


def _as_date(value) -> str | None:
    """Normalise a value to an ISO ``YYYY-MM-DD`` string, or ``None``."""
    if not value:
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


class WatermarkStore:
    """Per-spider "newest date seen so far" ledger, file-backed."""

    def __init__(self, path: str | Path = "data/watermarks"):
        self.dir = Path(path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__)

    def _file(self, spider: str) -> Path:
        return self.dir / f"{spider}.json"

    def get(self, spider: str) -> str | None:
        fp = self._file(spider)
        if not fp.exists():
            return None
        try:
            return json.loads(fp.read_text(encoding="utf-8")).get("watermark")
        except Exception:
            return None

    def update(self, spider: str, watermark: str) -> None:
        fp = self._file(spider)
        fp.write_text(
            json.dumps({"watermark": watermark}, ensure_ascii=False),
            encoding="utf-8",
        )

    def should_crawl(self, spider: str, item_date) -> bool:
        """Return ``True`` if ``item_date`` is strictly newer than the watermark."""
        wm = self.get(spider)
        d = _as_date(item_date)
        if d is None:
            return True  # unknown date -> keep (never silently drop)
        if wm is None:
            return True
        return d > wm


class IncrementalMixin:
    """Mix into a spider to skip items older than the last run's watermark.

    Usage::

        class MySpider(IncrementalMixin, BaseSpider):
            watermark_path = "data/watermarks"

        # in parse_detail, after building the item:
        if self.is_new(item):
            self.record_seen(item.get("pub_date"))
            yield item

    ``close_spider`` persists the highest date seen this run.
    """

    watermark_path: str = "data/watermarks"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._watermark = WatermarkStore(self.watermark_path)
        self._max_date: str | None = self._watermark.get(getattr(self, "name", ""))

    def is_new(self, item) -> bool:
        date_value = item.get("pub_date") if isinstance(item, dict) else getattr(
            item, "pub_date", None
        )
        return self._watermark.should_crawl(getattr(self, "name", ""), date_value)

    def record_seen(self, item_date) -> None:
        d = _as_date(item_date)
        if d and (self._max_date is None or d > self._max_date):
            self._max_date = d

    def close_spider(self, spider):
        if self._max_date:
            self._watermark.update(getattr(self, "name", ""), self._max_date)
        super().close_spider(spider)
