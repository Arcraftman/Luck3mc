"""Notify operators about *new* items discovered during a monitor run.

Positioned AFTER the deduplication pipeline (order 250 > 200), so only items
that survived de-duplication — i.e. genuinely new URLs — reach this pipeline.

Requires ``NOTIFY_ENABLED=True``. For cross-run "new" detection the crawler
must run with a database (``DATABASE_URL``); without it, de-dup is in-memory
and the same URLs would be re-notified on every monitor pass.
"""

from __future__ import annotations

from itemadapter import ItemAdapter

from crawler.notifiers import NotifyMessage, get_notifier
from crawler.utils.log_config import get_logger


class NotifyPipeline:
    def __init__(self, settings):
        self.enabled = bool(settings.getbool("NOTIFY_ENABLED"))
        self.settings = settings
        self.notifier = None
        self.logger = get_logger(__name__)
        if self.enabled:
            try:
                self.notifier = get_notifier(settings)
            except Exception as exc:  # noqa: BLE001
                self.logger.error("NotifyPipeline: failed to build notifier: %s", exc)
                self.enabled = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def open_spider(self, spider):
        if self.enabled and not self.settings.get("DATABASE_URL"):
            self.logger.warning(
                "NotifyPipeline: NOTIFY_ENABLED but no DATABASE_URL set. "
                "De-duplication is in-memory, so the SAME items will be "
                "re-notified on every monitor run. Run `scrapy createdb` "
                "(SQLite) to enable persistent de-dup."
            )

    def process_item(self, item, spider):
        if not self.enabled or self.notifier is None:
            return item
        adapter = ItemAdapter(item)
        message = NotifyMessage(
            title=adapter.get("title") or "",
            url=adapter.get("source_url") or "",
            pub_date=adapter.get("pub_date") or "",
            source_site=adapter.get("source_site")
            or getattr(spider, "source_site", ""),
        )
        if not message.url:
            return item
        ok = self.notifier.send(message)
        if ok:
            self.logger.info("Notified new item: %s", message.url)
        else:
            self.logger.warning("Notify FAILED for: %s", message.url)
        return item
