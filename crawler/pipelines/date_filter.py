"""Drop items whose publish date is not *today* (when ``CRAWL_TODAY_ONLY`` is on).

The scheduled ``scrapy monitor`` enables this so a daily pass only surfaces
items published that day and never the historical backlog (which would
otherwise flood notifications on the very first run).

Items without a parseable ``pub_date`` are **kept** (with a warning) so a
spider that fails to extract a date can never silently discard everything.
"""

from __future__ import annotations

from datetime import date

from itemadapter import ItemAdapter


class DateFilterPipeline:
    """Keep only items published today when ``CRAWL_TODAY_ONLY`` is set."""

    def __init__(self, crawl_today_only: bool = False):
        self.crawl_today_only = crawl_today_only

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.getbool("CRAWL_TODAY_ONLY", False))

    def process_item(self, item, spider):
        if not self.crawl_today_only:
            return item

        adapter = ItemAdapter(item)
        pub = adapter.get("pub_date")
        if not pub:
            spider.logger.warning(
                "[today-only] 无发布日期, 保留(未丢弃): %s",
                adapter.get("source_url") or adapter.get("title"),
            )
            return item

        try:
            pub_d = pub.date() if hasattr(pub, "date") else date.fromisoformat(str(pub)[:10])
        except (ValueError, TypeError, AttributeError):
            spider.logger.warning("[today-only] 发布日期无法解析 %r, 保留", pub)
            return item

        if pub_d == date.today():
            return item

        spider.logger.info(
            "[today-only] 丢弃非当天数据 (%s): %s",
            pub_d,
            adapter.get("source_url") or adapter.get("title"),
        )
        return None
