from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scrapy.http import HtmlResponse, Request
from scrapy.link import Link

from crawler.spiders.gov_categories import CaishuiSpider


@pytest.mark.parametrize("host", ["www.chinatax.gov.cn", "fgk.chinatax.gov.cn"])
def test_tax_homepage_only_follows_policy_links(host):
    spider = CaishuiSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    base = f"https://{host}"
    allowed = ["/zcfgk/c100006/listflfg.html", "/zcfgk/c100015/list_zcjd.html",
               "/zcfgk/c100012/c5252176/content.html"]
    denied = ["/chinatax/n810219/n810724/c5237806/content.html",
              "/search5/html/searchResult.html?searchWord=政策",
              "/chinatax/n810209/index.html", "/eng/home.html"]
    response = HtmlResponse(url=base + "/", encoding="utf-8", body=''.join(
        f'<a href="{path}">政策通知</a>' for path in allowed + denied).encode())
    requests = [r for r in spider._requests_to_follow(response) if r]
    assert {r.url for r in requests} == {base + path for path in allowed}
    for path in denied:
        assert spider.process_request(Request(base + path), response) is None
        assert list(spider.parse_page(response.replace(url=base + path))) == []
    detail = response.replace(url=base + allowed[-1])
    assert not [r for r in spider._requests_to_follow(detail) if r]
