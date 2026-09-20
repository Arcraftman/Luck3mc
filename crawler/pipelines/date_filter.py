"""Keep publications from 2026-01-01 through the frozen run start time."""
from datetime import date, datetime

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from crawler.utils.publication_time import BEIJING, parse_publication_time


class DateFilterPipeline:
    """Apply the global publication range before deduplication and storage."""

    def __init__(self, run_at=None, stats=None):
        self.run_at = parse_publication_time(run_at or datetime.now(BEIJING))
        if self.run_at is None:
            raise ValueError("CRAWL_RUN_AT must contain a valid date and time")
        self.floor = datetime(2026, 1, 1, tzinfo=BEIJING)
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("CRAWL_RUN_AT"), crawler.stats)

    def open_spider(self, spider):
        spider.logger.info(
            "[date-filter] Beijing publication range [%s, %s]",
            self.floor.isoformat(), self.run_at.isoformat(),
        )

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        precise_value = adapter.get("pub_datetime")
        date_value = adapter.get("pub_date")
        published = parse_publication_time(precise_value)
        reason = None
        display_value = precise_value or date_value

        if published is not None:
            if published < self.floor:
                reason = "before_2026"
            elif published > self.run_at:
                reason = "future_publication"
        else:
            try:
                published_date = date.fromisoformat(str(date_value)[:10])
            except (TypeError, ValueError):
                published_date = None
            if published_date is None:
                reason = "missing_or_unparseable_date"
            elif published_date < self.floor.date():
                reason = "before_2026"
            elif published_date > self.run_at.date():
                reason = "future_publication"
        if reason:
            if self.stats:
                self.stats.inc_value(f"date_filter/dropped/{reason}")
            raise DropItem(
                f"[date-filter] {reason}: {display_value!r} "
                f"{adapter.get('source_url', '')}"
            )
        if self.stats:
            self.stats.inc_value("date_filter/accepted")
        return item
