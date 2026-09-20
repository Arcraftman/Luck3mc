"""Drop duplicate items.

Two modes, selected automatically:

* **Persistent (default when ``DATABASE_URL`` is set):** a ``crawled_urls``
  ledger in the database makes de-duplication survive crawler restarts and run
  across multiple spiders / machines. This is what makes the framework safe to
  run on a schedule without re-ingesting everything.
* **In-memory:** when no database is configured, a process-local ``set`` is
  used (de-dupes within a single crawl only).
"""

import hashlib

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from sqlalchemy import select

from crawler.db.models import CrawledUrl
from crawler.utils.log_config import get_logger


class DeduplicatePipeline:
    """Skip items whose ``source_url`` we've already stored."""

    def __init__(self, database_url: str = ""):
        self.database_url = database_url
        self.use_db = False
        self.engine = None
        self.Session = None
        self.seen: set = set()
        self.duplicates = 0

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("DATABASE_URL", ""))

    def open_spider(self, spider):
        if self.database_url:
            try:
                from crawler.db.session import get_engine, get_sessionmaker

                self.engine = get_engine(self.database_url)
                self.Session = get_sessionmaker(self.engine)
                self.use_db = True
                self.logger = get_logger(__name__)
                self.logger.info("DeduplicatePipeline: persistent (database) store.")
                return
            except Exception as exc:  # noqa: BLE001 - fall back to memory
                spider.logger.warning(
                    "DeduplicatePipeline: DB unavailable (%s); using in-memory store.", exc
                )
        else:
            spider.logger.info("DeduplicatePipeline: in-memory store.")
        self.logger = get_logger(__name__)

    def _fingerprint(self, adapter: ItemAdapter) -> str:
        key = adapter.get("source_url") or adapter.get("title") or ""
        return hashlib.sha256(str(key).encode("utf-8")).hexdigest()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if not self.use_db:
            fp = self._fingerprint(adapter)
            if fp in self.seen:
                self.duplicates += 1
                spider.logger.debug("Skipping duplicate: %s", adapter.get("source_url"))
                raise DropItem("Duplicate item")
            self.seen.add(fp)
            return item

        # Persistent mode: consult the crawled_urls ledger.
        url = adapter.get("source_url")
        source_site = adapter.get("source_site") or getattr(spider, "source_site", "")
        if not url:
            return item
        session = self.Session()
        try:
            exists = session.execute(
                select(CrawledUrl).where(
                    CrawledUrl.url == url,
                    CrawledUrl.source_site == source_site,
                )
            ).scalar_one_or_none()
            if exists is not None:
                self.duplicates += 1
                spider.logger.debug("Skipping already-crawled URL: %s", url)
                raise DropItem("Already-crawled URL")
            session.add(CrawledUrl(url=url, source_site=source_site))
            session.commit()
        except DropItem:
            raise
        except Exception as exc:  # noqa: BLE001 - on DB error, keep the item
            session.rollback()
            spider.logger.error("DeduplicatePipeline DB error: %s", exc)
        finally:
            session.close()
        return item

    def close_spider(self, spider):
        if self.duplicates:
            self.logger.info("DeduplicatePipeline skipped %d duplicates.", self.duplicates)
