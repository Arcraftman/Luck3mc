"""Custom Scrapy extensions.

Extensions hook into the crawl lifecycle for cross-cutting concerns like
metrics, alerts, or audit logging without polluting spiders.
"""

from scrapy import signals  # type: ignore

from crawler.utils.log_config import get_logger


class StatsLoggingExtension:
    """Log a consolidated stats summary when the crawl finishes."""

    def __init__(self, stats):
        self.stats = stats
        self.logger = get_logger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls(crawler.stats)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_closed(self, spider, reason):
        self.logger.info(
            "Spider '%s' closed (reason=%s). Items: %d, Requests: %d, Errors: %d",
            spider.name,
            reason,
            self.stats.get_value("item_scraped_count", 0),
            self.stats.get_value("response_received_count", 0),
            self.stats.get_value("spider_exceptions_count", 0),
        )
        skipped = self.stats.get_value("incremental/skipped_known_detail", 0)
        if skipped:
            self.logger.info("Spider '%s': 下载前跳过 %d 个已采集详情链接。", spider.name, skipped)
        archive_pages = self.stats.get_value("incremental/skipped_archive_pages", 0)
        if archive_pages:
            self.logger.info("Spider '%s': 增量模式跳过 %d 个历史列表页。",
                             spider.name, archive_pages)
