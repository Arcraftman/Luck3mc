"""Persist items to durable storage.

``JsonLinesExportPipeline`` is the always-on sink (one JSON object per line,
great for streaming into a data warehouse). ``DatabasePipeline`` performs an
idempotent upsert into the relational store (see :mod:`crawler.db`). It is a
no-op with a warning when ``DATABASE_URL`` is not configured, so enabling it
in production settings is safe even before a database exists.
"""

import json
from datetime import datetime
from pathlib import Path

from itemadapter import ItemAdapter
from sqlalchemy import select

from crawler.db.models import TaxRecord
from crawler.utils.log_config import get_logger


class JsonLinesExportPipeline:
    """Append each item as a JSON line under ``OUTPUT_DIR/<spider>/<date>.jsonl``."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.handles: dict = {}
        self.counts: dict = {}
        self.logger = get_logger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        output_dir = settings.get("OUTPUT_DIR", str(Path("data")))
        return cls(output_dir)

    def _path_for(self, spider) -> Path:
        date = datetime.now().strftime("%Y-%m-%d")
        sub = self.output_dir / spider.name
        sub.mkdir(parents=True, exist_ok=True)
        return sub / f"{date}.jsonl"

    def process_item(self, item, spider):
        path = self._path_for(spider)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(ItemAdapter(item)), ensure_ascii=False) + "\n")
        self.counts[spider.name] = self.counts.get(spider.name, 0) + 1
        return item

    def close_spider(self, spider):
        total = self.counts.get(spider.name, 0)
        self.logger.info("JsonLinesExportPipeline wrote %d items for %s.", total, spider.name)


class DatabasePipeline:
    """Idempotent upsert of items into the relational store.

    Upsert key: ``(source_url, item_type)`` — re-crawling the same page updates
    the existing row instead of creating a duplicate.
    """

    # Item field -> TaxRecord column (None fields are skipped if absent).
    _COLUMNS = (
        "title", "doc_number", "pub_date", "effective_date", "category",
        "issuing_authority", "summary", "author", "business_type",
        "processing_time_limit", "content",
    )

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.Session = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("DATABASE_URL", ""))

    def open_spider(self, spider):
        if not self.database_url:
            spider.logger.warning(
                "DatabasePipeline: DATABASE_URL not set; pipeline is a no-op."
            )
            return
        try:
            from crawler.db.session import get_engine, get_sessionmaker

            self.engine = get_engine(self.database_url)
            self.Session = get_sessionmaker(self.engine)
            spider.logger.info("DatabasePipeline connected to %s", self.database_url)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            spider.logger.error("DatabasePipeline failed to connect: %s", exc)
            self.engine = None
            self.Session = None

    def _row_data(self, adapter: ItemAdapter, spider) -> dict:
        item_type = adapter.get("item_type") or type(adapter.item).__name__.replace("Item", "")
        data = {
            "item_type": item_type,
            "title": adapter.get("title"),
            "source_url": adapter.get("source_url"),
            "source_site": adapter.get("source_site")
            or getattr(spider, "source_site", ""),
        }
        for col in self._COLUMNS:
            data[col] = adapter.get(col)
        data["raw"] = json.dumps(dict(adapter), ensure_ascii=False)
        return data

    def process_item(self, item, spider):
        if self.Session is None:
            return item
        adapter = ItemAdapter(item)
        source_url = adapter.get("source_url")
        if not source_url:
            return item
        data = self._row_data(adapter, spider)

        session = self.Session()
        try:
            existing = session.execute(
                select(TaxRecord).where(
                    TaxRecord.source_url == data["source_url"],
                    TaxRecord.item_type == data["item_type"],
                )
            ).scalar_one_or_none()
            if existing is not None:
                for key, value in data.items():
                    if key in ("id", "created_at"):
                        continue
                    setattr(existing, key, value)
            else:
                session.add(TaxRecord(**data))
            session.commit()
        except Exception as exc:  # noqa: BLE001 - don't kill the crawl on DB error
            session.rollback()
            spider.logger.error(
                "DatabasePipeline upsert failed for %s: %s", source_url, exc
            )
        finally:
            session.close()
        return item

    def close_spider(self, spider):
        if self.engine is not None:
            self.engine.dispose()
