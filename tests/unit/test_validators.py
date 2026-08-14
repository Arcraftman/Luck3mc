"""Unit tests for data validators and item processing."""

from crawler.items import TaxPolicyItem
from crawler.utils.data_validators import (
    clean_text,
    normalize_url,
    parse_pub_date,
    to_int_or_none,
)
from itemloaders import ItemLoader


def test_clean_text_collapses_whitespace():
    assert clean_text("  hello   world\n") == "hello world"
    assert clean_text("") is None


def test_parse_pub_date_chinese_and_iso():
    assert parse_pub_date("2026年08月11日") == "2026-08-11"
    assert parse_pub_date("2026-08-11") == "2026-08-11"
    assert parse_pub_date("2026/8/11 10:30") == "2026-08-11"
    assert parse_pub_date("not a date") is None


def test_normalize_url_adds_scheme_and_strips_fragment():
    assert normalize_url("chinatax.gov.cn/x") == "https://chinatax.gov.cn/x"
    assert normalize_url("https://a.com/p#frag") == "https://a.com/p"


def test_to_int_or_none():
    assert to_int_or_none("办理时限：30 个工作日") == 30
    assert to_int_or_none("none") is None


def test_tax_policy_item_loads_cleanly():
    loader = ItemLoader(item=TaxPolicyItem())
    loader.add_value("title", "  关于增值税  政策的通知  ")
    loader.add_value("pub_date", "2026年08月11日")
    loader.add_value("source_url", "https://www.chinatax.gov.cn/p#x")
    item = loader.load_item()
    assert item["title"] == "关于增值税 政策的通知"
    assert item["pub_date"] == "2026-08-11"
    assert item["source_url"] == "https://www.chinatax.gov.cn/p"
