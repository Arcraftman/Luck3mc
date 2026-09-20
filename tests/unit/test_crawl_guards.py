from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scrapy.exceptions import IgnoreRequest
from scrapy.http import HtmlResponse, Request

from crawler.middlewares.site_guard import SiteGuardMiddleware
from crawler.spiders.gov_categories import GaoqiSpider, KexiaoSpider
from crawler.utils.compliance import is_compliance_blocked
from crawler.utils.policy_classify import is_policy_document


def test_login_widget_does_not_block_public_homepage():
    html = '''<title>政策公开首页</title><div><input placeholder="验证码"></div>
      <script>var message="Access Denied 安全验证";</script>
      <a href="/1">政策文件</a><a href="/2">公示公告</a><a href="/3">更多</a>'''
    assert not is_compliance_blocked(html)


@pytest.mark.parametrize("html,status", [
    ('<title>人机验证</title><input placeholder="验证码">', 200),
    ('<title>用户登录</title><input type="password">', 200),
    ('<body>您的请求已被阻断</body>', 200),
    ('Access denied', 403),
    ('Too many requests', 429),
])
def test_actual_access_walls_are_blocked(html, status):
    assert is_compliance_blocked(html, status)


def test_one_blocked_host_does_not_stop_other_sources_or_retry():
    spider = GaoqiSpider()
    spider.crawler = SimpleNamespace(stats=Mock())
    guard = SiteGuardMiddleware()
    first, second = spider.allowed_domains[:2]
    request = Request(f"https://{first}/file")
    response = HtmlResponse(url=request.url, status=403, body=b"Access Denied")
    with pytest.raises(IgnoreRequest):
        guard.process_response(request, response, spider)
    assert request.meta["dont_retry"]
    with pytest.raises(IgnoreRequest):
        guard.process_request(Request(f"https://{first}/other"), spider)
    assert guard.process_request(Request(f"https://{second}/file"), spider) is None
    assert second not in spider.blocked_domains


def test_public_routes_and_detail_only_extraction():
    spider = KexiaoSpider()
    assert spider.is_public_url("https://zjtx.miit.gov.cn/zxqySy/tzggView?id=abc")
    assert not spider.is_public_url("https://zjtx.miit.gov.cn/qyxx/gotoFzal")
    assert "https://zjtx.miit.gov.cn/zxqySy/tzggMore" in spider.start_urls
    response = HtmlResponse(url="https://zjtx.miit.gov.cn/zxqySy/tzggMore",
                            body=("<h1>通知公告</h1><p>通知政策" * 100).encode(), encoding="utf-8")
    assert list(spider.parse_page(response)) == []
    detail = HtmlResponse(url="https://zjtx.miit.gov.cn/zxqySy/tzggView?id=abc")
    assert spider.process_request(Request(spider.start_urls[-1]), detail) is None


@pytest.mark.parametrize("path", ["list_gsgg_l2.shtml", "list_zcwj.shtml", "index.html", ""])
def test_list_page_never_becomes_policy_even_with_document_keywords(path):
    assert not is_policy_document(f"https://example.gov.cn/zhengce/{path}",
                                  "问题中介机构公告", "通知正文" * 100)
