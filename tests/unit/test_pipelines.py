"""Unit tests for the validation and de-duplication pipelines."""

import logging

from crawler.items import TaxPolicyItem
from crawler.pipelines.deduplication import DeduplicatePipeline
from crawler.pipelines.validation import ValidationPipeline
from itemloaders import ItemLoader


class FakeSpider:
    logger = logging.getLogger("test_pipelines")


def _policy_item(url, title="标题"):
    il = ItemLoader(item=TaxPolicyItem())
    il.add_value("title", title)
    il.add_value("source_url", url)
    return il.load_item()


def test_validation_drops_item_missing_required_fields():
    p = ValidationPipeline()
    # Missing both required fields (title, source_url).
    il = ItemLoader(item=TaxPolicyItem())
    il.add_value("content", "正文内容")
    item = il.load_item()

    assert p.process_item(item, FakeSpider()) is None
    assert p.dropped == 1


def test_validation_keeps_valid_item():
    p = ValidationPipeline()
    item = _policy_item("https://x.com/a")
    assert p.process_item(item, FakeSpider()) is item
    assert p.dropped == 0


def test_dedup_in_memory_drops_duplicate():
    p = DeduplicatePipeline(database_url="")  # no DB -> in-memory mode
    p.open_spider(FakeSpider())

    first = p.process_item(_policy_item("https://x.com/a"), FakeSpider())
    assert first is not None

    second = p.process_item(_policy_item("https://x.com/a"), FakeSpider())
    assert second is None  # duplicate dropped
    assert p.duplicates == 1


def test_dedup_in_memory_keeps_distinct():
    p = DeduplicatePipeline(database_url="")
    p.open_spider(FakeSpider())
    assert p.process_item(_policy_item("https://x.com/a"), FakeSpider()) is not None
    assert p.process_item(_policy_item("https://x.com/b"), FakeSpider()) is not None
    assert p.duplicates == 0
