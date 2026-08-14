"""ORM models for persisted crawl data.

Two tables matter for the framework:

* ``tax_records`` — the deduplicated, canonical store of extracted items.
  Uniqueness is enforced on ``(source_url, item_type)`` so re-crawling the
  same page is an idempotent upsert, never a duplicate row.
* ``crawled_urls`` — a lightweight visited-URL ledger used by
  :class:`crawler.pipelines.deduplication.DeduplicatePipeline` for
  *cross-run* deduplication (survives crawler restarts).
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from crawler.db.base import Base


class TaxRecord(Base):
    """A stored, de-duplicated tax item (policy / announcement / news / guide)."""

    __tablename__ = "tax_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_site: Mapped[str] = mapped_column(String(128), nullable=False)

    # Optional, domain-specific fields (shared column set keeps one table).
    doc_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pub_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ISO YYYY-MM-DD
    effective_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processing_time_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[str | None] = mapped_column(Text, nullable=True)  # full item as JSON

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("source_url", "item_type", name="uq_tax_records_url_type"),
    )


class CrawledUrl(Base):
    """Visited-URL ledger for cross-run deduplication."""

    __tablename__ = "crawled_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_site: Mapped[str] = mapped_column(String(128), nullable=False)
    item_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("url", "source_site", name="uq_crawled_urls"),
    )
