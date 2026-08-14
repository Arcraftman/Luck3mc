"""Date-based item gating.

Two orthogonal, independently-configurable gates (both off by default so the
pipeline is a no-op unless explicitly enabled):

* ``CRAWL_TODAY_ONLY`` — keep only items published *today* (used by the
  scheduled daily ``monitor`` pass so the historical backlog never floods the
  report on the first run).
* ``CRAWL_FROM_DATE`` — drop items published *before* this date (e.g.
  ``2026-01-01``). Used for a "only keep policies from date X onward" sweep.

Items without a parseable ``pub_date`` are **kept** (with a warning) so a
spider that fails to extract a date can never silently discard everything.
The gate logic here is the single source of truth; the thresholds are injected
from settings, so this module stays decoupled from any specific policy date.
"""

from __future__ import annotations

from datetime import date

from itemadapter import ItemAdapter


def _parse_pub_date(pub) -> date | None:
    """Best-effort parse of ``pub_date`` into a ``date``; None if unparseable."""
    if pub is None:
        return None
    if hasattr(pub, "date"):  # datetime / date instance
        return pub.date() if hasattr(pub, "year") is False else pub
    if isinstance(pub, date):
        return pub
    try:
        return date.fromisoformat(str(pub)[:10])
    except (ValueError, TypeError):
        return None


class DateFilterPipeline:
    """Drop items that fall outside the configured date window."""

    def __init__(self, crawl_today_only: bool = False, crawl_from_date: str = ""):
        self.crawl_today_only = crawl_today_only
        # Parse the lower-bound date once at construction; invalid values
        # degrade to "no lower bound" (with a warning via the spider later).
        self.from_date = _parse_pub_date(crawl_from_date) if crawl_from_date else None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler.settings.getbool("CRAWL_TODAY_ONLY", False),
            crawler.settings.get("CRAWL_FROM_DATE", "") or "",
        )

    def process_item(self, item, spider):
        if not self.crawl_today_only and self.from_date is None:
            return item

        adapter = ItemAdapter(item)
        pub = adapter.get("pub_date")
        if not pub:
            spider.logger.warning(
                "[date-filter] 无发布日期, 保留(未丢弃): %s",
                adapter.get("source_url") or adapter.get("title"),
            )
            return item

        pub_d = _parse_pub_date(pub)
        if pub_d is None:
            spider.logger.warning("[date-filter] 发布日期无法解析 %r, 保留", pub)
            return item

        # Gate 1: today-only
        if self.crawl_today_only and pub_d != date.today():
            spider.logger.info(
                "[date-filter] 丢弃非当天数据 (%s): %s",
                pub_d,
                adapter.get("source_url") or adapter.get("title"),
            )
            return None

        # Gate 2: lower-bound (keep >= from_date)
        if self.from_date is not None and pub_d < self.from_date:
            spider.logger.info(
                "[date-filter] 丢弃早于 %s 的数据 (%s): %s",
                self.from_date.isoformat(),
                pub_d,
                adapter.get("source_url") or adapter.get("title"),
            )
            return None

        return item
