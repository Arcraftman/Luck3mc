"""Tests for the generic gov_policy_root spider's page classifier/extractor."""

from types import SimpleNamespace

from scrapy.http import HtmlResponse, Request
from scrapy.link import Link

from crawler.spiders.gov_policy.root_spider import GovPolicyRootSpider

_POLICY_HTML = """<html><head><title>测试办法_中国政府网</title></head><body>
<div class="pages_content">现将《测试办法》印发给你们，请遵照执行。
第一条 为规范相关活动，制定本办法。第二条 本办法适用于全国范围。
第三条 主管部门应当加强监督检查。第四条 违反本办法的，依法处理。
第五条 本办法自公布之日起施行。第六条 既往规定与本办法不一致的，以本办法为准。
第七条 本办法由主管部门负责解释。第八条 各级单位应当做好宣传工作。
第九条 鼓励社会参与监督。第十条 本办法有效期五年。第十一条 各级财政部门应当保障经费。
第十二条 本办法所称相关活动，是指面向社会提供的公共服务事项。第十三条 实施单位应当公开服务标准。
第十四条 公民、法人或其他组织认为实施单位违反本办法的，可以投诉举报。第十五条 监督管理部门应当建立评估机制。
第十六条 本办法自发布之日起三十日后施行。第十七条 此前有关规定与本办法不一致的，以本办法为准。
第十八条 国务院有关部门应当加强指导。第十九条 地方各级人民政府应当结合实际制定配套措施。第二十条 本办法解释权归主管部门。</div>
</body></html>"""

_NEWS_HTML = """<html><head><title>本市举办科技创新主题活动_新闻</title></head><body>
<div class="pages_content">记者从现场获悉，昨日举办了科技创新主题活动，现场气氛热烈。
与会嘉宾纷纷表示，活动很有意义。主办方表示将持续举办此类活动，推动产学研合作。
本次活动的成功举办，得到各方高度评价。未来还将组织更多交流。</div>
</body></html>"""

_LISTING_HTML = """<html><head><title>政策文件</title></head><body>
<div class="pages_content">政策文件列表</div>
<ul><li><a href="content_1.htm">某办法</a></li></ul>
</body></html>"""


def _response(url: str, html: str) -> HtmlResponse:
    return HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8")


def test_parse_page_keeps_policy_document():
    spider = GovPolicyRootSpider()
    resp = _response("https://www.gov.cn/zhengce/2026-08/content_1.htm", _POLICY_HTML)
    items = list(spider.parse_page(resp))
    assert len(items) == 1
    item = items[0]
    assert "测试办法" in (item.get("title") or "")
    assert "https://www.gov.cn/zhengce/2026-08/content_1.htm" == item.get("source_url")
    # source_site resolved from the gov.cn root's name in roots.yaml.
    assert item.get("source_site") == "gov_zhengce"


def test_parse_page_drops_news_page():
    spider = GovPolicyRootSpider()
    resp = _response("https://www.gov.cn/xinwen/2026-08/content_2.htm", _NEWS_HTML)
    items = list(spider.parse_page(resp))
    assert items == []


def test_parse_page_drops_listing_page():
    spider = GovPolicyRootSpider()
    resp = _response("https://www.gov.cn/zhengce/", _LISTING_HTML)
    items = list(spider.parse_page(resp))
    assert items == []


def test_parse_page_ignores_non_html():
    spider = GovPolicyRootSpider()
    from scrapy.http import Response

    resp = Response(url="https://www.gov.cn/zhengce/2026-08/content_3.pdf")
    assert list(spider.parse_page(resp)) == []


def test_process_links_drops_explicit_pre_2026_archives():
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(
        stats=type("Stats", (), {"inc_value": lambda self, key: None})()
    )
    links = [
        Link("https://www.gov.cn/zhengce/2025/content_1.htm"),
        Link("https://www.gov.cn/zhengce/202509/content_2.htm"),
        Link("https://www.gov.cn/zhengce/qtwj2014/content_3.htm"),
        Link("https://www.gov.cn/zhengce/2026/content_4.htm"),
        Link("https://www.gov.cn/zhengce/latest/content_5.htm"),
    ]
    assert [link.url for link in spider.process_links(links)] == [
        "https://www.gov.cn/zhengce/2026/content_4.htm",
        "https://www.gov.cn/zhengce/latest/content_5.htm",
    ]


def test_current_url_with_old_reference_is_not_dropped():
    spider = GovPolicyRootSpider()
    assert not spider._is_explicitly_old_url(
        "https://www.gov.cn/zhengce/2026/revising-rule-2016.html"
    )


def test_process_request_rejects_old_url_before_download():
    spider = GovPolicyRootSpider()
    spider.crawler = SimpleNamespace(
        stats=type("Stats", (), {"inc_value": lambda self, key: None})()
    )
    response = _response("https://www.gov.cn/zhengce/", _LISTING_HTML)
    assert spider.process_request(
        Request("https://www.gov.cn/zhengce/2024/content_1.htm"), response
    ) is None
