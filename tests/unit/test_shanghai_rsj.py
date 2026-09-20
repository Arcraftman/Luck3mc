from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scrapy.http import HtmlResponse
from scrapy.settings import Settings

from crawler.spiders.gov_policy.root_spider import GovPolicyRootSpider
from crawler.utils.policy_parse import extract_pub_datetime
from crawler.utils.policy_classify import is_policy_document


@pytest.mark.parametrize("section", ["tzcjd_17351", "tzxgkxx_17197"])
def test_rsj_additional_sections_discover_details_and_pagination(section):
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(stats=Mock(), settings=Settings())
    url = f"https://rsj.sh.gov.cn/{section}/index.html"
    assert url in spider.start_urls
    detail = "https://rsj.sh.gov.cn/tzcjd_17352_17352/20260812/t0035_1443066.html"
    response = HtmlResponse(url=url, encoding="utf-8", body=(
        '<script>var options={totalPage: 2};</script>'
        f'<a href="{detail}">政策问答</a>').encode())
    urls = {r.url for r in spider._requests_to_follow(response) if r}
    assert detail in urls
    assert f"https://rsj.sh.gov.cn/{section}/index_2.html" in urls
    assert not list(spider.parse_page(response))
    assert is_policy_document(detail, "2026年度节日补助费相关政策问答", "政策说明" * 30)


def test_rsj_widget_pagination_and_public_routes():
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    url = "https://rsj.sh.gov.cn/tgwgfx_17726/index.html"
    response = HtmlResponse(url=url, encoding="utf-8", body=b'''
        <script>$(".pagination").pagination({totalPage: 3});</script>
        <a href="/tshbx_17729/20260812/t0035_1443067.html">policy</a>
        <a href="/txwfb_1/20260812/news.html">news</a>''')
    requests = [r for r in spider._requests_to_follow(response) if r]
    assert {r.url for r in requests} == {
        "https://rsj.sh.gov.cn/tshbx_17729/20260812/t0035_1443067.html",
        "https://rsj.sh.gov.cn/tgwgfx_17726/index_2.html",
        "https://rsj.sh.gov.cn/tgwgfx_17726/index_3.html",
    }
    assert list(spider.parse_page(response)) == []
    assert not spider.is_public_url("https://rsj.sh.gov.cn/txwfb_1/index.html")
    assert requests[-2].priority > requests[-1].priority


def test_rsj_incremental_scan_caps_large_archives_at_three_pages():
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    url = "https://rsj.sh.gov.cn/tzxgkxx_17197/index.html"
    response = HtmlResponse(url=url, encoding="utf-8",
                            body=b'<script>var options={totalPage: 131};</script>')
    requests = [r for r in spider._requests_to_follow(response) if r]
    assert [r.url for r in requests] == [
        "https://rsj.sh.gov.cn/tzxgkxx_17197/index_2.html",
        "https://rsj.sh.gov.cn/tzxgkxx_17197/index_3.html",
    ]
    spider.crawler.stats.inc_value.assert_called_with(
        "incremental/skipped_archive_pages", 128
    )


def test_rsj_metadata_preserves_minutes_and_overrides_body_dates():
    response = HtmlResponse(url="https://example.org/detail", encoding="utf-8", body='''
        <meta name="PubDate" content="2026-08-06 13∶08">
        <body>发布时间：2026-08-06<p>2026年8月16日起施行</p></body>'''.encode())
    assert extract_pub_datetime(response) == "2026-08-06T13:08:00+08:00"
