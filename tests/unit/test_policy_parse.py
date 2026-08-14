"""Unit tests for :mod:`crawler.utils.policy_parse` against real fixtures.

These pin down the site-agnostic extraction helpers (title cleanup, publish
date normalisation, content container scoring, document-number / issuing
authority sniffing) so a regression in the shared parsing layer is caught
without a network crawl.
"""

from pathlib import Path

import pytest
from crawler.utils.policy_parse import (
    extract_content,
    extract_doc_number,
    extract_issuing_authority,
    extract_pub_date,
    extract_title,
    find_next_page,
    iter_detail_links,
)
from scrapy.http import HtmlResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _response(fixture: str, url: str = "http://example.gov.cn/x/index.html") -> HtmlResponse:
    body = (FIXTURES / fixture).read_bytes()
    return HtmlResponse(url=url, body=body, encoding="utf-8")


def test_extract_title_strips_site_suffix():
    resp = _response("most_qykjzc_detail.html")
    title = extract_title(resp)
    assert title
    assert "中华人民共和国科学技术部" not in title
    assert "通知" in title


def test_extract_pub_date_normalises_chinese_format():
    resp = _response("most_qykjzc_detail.html")
    date = extract_pub_date(resp)
    assert date == "2026-02-23"


def test_extract_content_prefers_xxgk_detail_container():
    resp = _response("most_qykjzc_detail.html")
    content = extract_content(resp)
    assert len(content) > 1000
    # The recognised container yields the regulation body, not nav chrome.
    assert "科技保险" in content or "高技术" in content


def test_iter_detail_links_matches_xxgk_paths():
    resp = _response(
        "most_qykjzc_list.html",
        url="http://www.most.gov.cn/ztzl/qykjzc/index.html",
    )
    urls = [u for u, _t, _d in iter_detail_links(resp, [
        __import__("re").compile(r"/xxgk/.*/t\d{8}_\d+\.html$"),
    ])]
    assert urls, "expected at least one detail link"
    assert all("/xxgk/" in u for u in urls)
    assert all(u.startswith("http") for u in urls)


def test_iter_detail_links_sniffs_list_row_date():
    resp = _response(
        "most_qykjzc_list.html",
        url="http://www.most.gov.cn/ztzl/qykjzc/index.html",
    )
    rows = list(iter_detail_links(resp, [
        __import__("re").compile(r"/xxgk/.*/t\d{8}_\d+\.html$"),
    ]))
    # At least some rows print a date next to the title.
    assert any(d for _u, _t, d in rows)


def test_find_next_page_absent_on_most_list():
    resp = _response(
        "most_qykjzc_list.html",
        url="http://www.most.gov.cn/ztzl/qykjzc/index.html",
    )
    assert find_next_page(resp) is None


def test_extract_doc_number_and_authority_on_miit_detail():
    resp = _response("miit_detail.html")
    # Miit detail bodies may not carry a 〔2026〕N号; helper must be safe.
    assert extract_doc_number(resp) is None or "号" in extract_doc_number(resp)
    # Authority label may be absent on some templates; helper must not raise.
    assert extract_issuing_authority(resp) is None or isinstance(
        extract_issuing_authority(resp), str
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("发布日期：2026年02月23日", "2026-02-23"),
        ("2026-02-23", "2026-02-23"),
        ("2026/3/5", "2026-03-05"),
    ],
)
def test_pub_date_normalisation_variants(raw, expected):
    html = f"<html><body><p>{raw}</p></body></html>"
    resp = HtmlResponse(url="http://x/y.html", body=html.encode("utf-8"))
    assert extract_pub_date(resp) == expected
