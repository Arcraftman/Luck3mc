from datetime import datetime
from importlib import import_module
from unittest.mock import Mock

import pytest
from scrapy.exceptions import DropItem
from scrapy.http import HtmlResponse

from crawler.pipelines.date_filter import DateFilterPipeline
from crawler.utils.policy_parse import extract_pub_datetime
from crawler.utils.publication_time import parse_publication_time


@pytest.mark.parametrize("timestamp,accepted", [
    ("2026-01-01 00:00:00", True),
    ("2026-01-01T00:00:00+08:00", True),
    ("2026-05-08 12:00:00", True),
    ("2026-09-17 12:04:59", True),
    ("2026-09-17 12:05:00", True),
    ("2026-09-17 12:05:01", False),
    ("2025-12-31T16:00:00Z", True),
    ("2026-09-17T04:05:01Z", False),
    (None, False),
    ("invalid", False),
    ("2026-02-30 12:00", False),
    ("2025-12-31 13:00", False),
])
def test_global_publication_range(timestamp, accepted):
    pipeline = DateFilterPipeline("2026-09-17 12:05:00")
    item = {"pub_datetime": timestamp, "source_url": "https://example.org/file"}
    if accepted:
        assert pipeline.process_item(item, None) is item
    else:
        with pytest.raises(DropItem):
            pipeline.process_item(item, None)


def test_before_noon_never_accepts_future_publication():
    pipeline = DateFilterPipeline("2026-09-17 09:00:00")
    assert pipeline.process_item({"pub_datetime": "2026-09-17 09:00:00"}, None)
    with pytest.raises(DropItem, match="future_publication"):
        pipeline.process_item({"pub_datetime": "2026-09-17 09:00:01"}, None)


def test_global_floor_at_new_year():
    pipeline = DateFilterPipeline("2026-01-01 12:01:00")
    with pytest.raises(DropItem, match="before_2026"):
        pipeline.process_item({"pub_datetime": "2025-12-31 23:59:59"}, None)
    assert pipeline.process_item({"pub_datetime": "2026-01-01 00:00:00"}, None)


@pytest.mark.parametrize("published,accepted", [
    ("2026-01-01", True),
    ("2026-09-17", True),
    ("2025-12-31", False),
    ("2026-09-18", False),
])
def test_date_only_publications_are_supported(published, accepted):
    pipeline = DateFilterPipeline("2026-09-17 12:00")
    item = {"pub_date": published}
    if accepted:
        assert pipeline.process_item(item, None) is item
    else:
        with pytest.raises(DropItem):
            pipeline.process_item(item, None)


def test_missing_date_is_counted():
    stats = Mock()
    pipeline = DateFilterPipeline("2026-09-17 12:00", stats)
    with pytest.raises(DropItem, match="missing_or_unparseable_date"):
        pipeline.process_item({}, None)
    stats.inc_value.assert_called_once_with("date_filter/dropped/missing_or_unparseable_date")


@pytest.mark.parametrize("raw,expected", [
    ("2026/9/17 10:30", "2026-09-17T10:30:00+08:00"),
    ("2026年9月17日 10:30:15", "2026-09-17T10:30:15+08:00"),
    ("2026-09-17T02:30:00Z", "2026-09-17T10:30:00+08:00"),
    ("2026-09-17T10:30:00+0800", "2026-09-17T10:30:00+08:00"),
    (datetime(2026, 9, 17, 10, 30), "2026-09-17T10:30:00+08:00"),
])
def test_timestamp_normalization(raw, expected):
    assert parse_publication_time(raw).isoformat() == expected


@pytest.mark.parametrize("html,expected", [
    ('<meta name="PubDate" content="2026-09-17 10:30">', "2026-09-17T10:30:00+08:00"),
    ('<meta property="article:published_time" content="2026-09-17T02:30:00Z">', "2026-09-17T10:30:00+08:00"),
    ('<p>发布时间：<span>2026-09-17 10:30</span></p>', "2026-09-17T10:30:00+08:00"),
    ('<p>发文日期：2026-09-17 10:30</p>', None),
    ('<p>发布时间：2026-09-17</p><p>会议时间：2026-09-17 10:30</p>', None),
    ('<script>发布时间：2026-09-17 10:30</script>', None),
])
def test_extract_only_publication_timestamp(html, expected):
    response = HtmlResponse(url="https://example.org/file", encoding="utf-8",
                            body=f"<html><body>{html}</body></html>".encode())
    assert extract_pub_datetime(response) == expected


@pytest.mark.parametrize("environment", ["base", "development", "production", "testing"])
def test_filter_runs_before_dedup_in_every_environment(environment):
    module = import_module(f"crawler.settings.{environment}")
    pipelines = module.ITEM_PIPELINES
    assert pipelines["crawler.pipelines.date_filter.DateFilterPipeline"] < pipelines[
        "crawler.pipelines.deduplication.DeduplicatePipeline"]
