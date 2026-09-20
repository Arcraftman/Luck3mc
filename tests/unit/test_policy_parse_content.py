"""Unit tests for :func:`crawler.utils.policy_parse.extract_content`.

Uses an inline HTML fixture (no network, no external file) so the container
scoring logic is pinned independently of the on-disk fixture set.
"""

from __future__ import annotations

from crawler.utils.policy_parse import extract_content
from scrapy.http import HtmlResponse

# A document whose real article body sits in a ``.article`` container (one of
# the recognised ``_CONTENT_CONTAINERS``), while nav/footer chrome sits outside
# it. The helper should score the container with the most text.
_SAMPLE_HTML = """<html><head><title>关于促进以旧换新的通知 - 某机关</title></head>
<body>
  <nav>首页 | 政策 | 公开 | 联系我们</nav>
  <div class="article">
    <h1>关于促进汽车以旧换新补贴的通知</h1>
    <p>为提振消费，对报废旧车并购买新车的个人给予一次性补贴。</p>
    <p>补贴标准为每辆新能源汽车补贴 10000 元，燃油车补贴 7000 元。</p>
    <p>申报材料包括身份证明、旧车回收证明与新车购车发票。</p>
  </div>
  <footer>版权所有 © 某机关</footer>
</body></html>"""


def _response() -> HtmlResponse:
    return HtmlResponse(
        url="http://example.gov.cn/x/notice.html",
        body=_SAMPLE_HTML.encode("utf-8"),
        encoding="utf-8",
    )


def test_extract_content_returns_body_text():
    text = extract_content(_response())
    assert "关于促进汽车以旧换新补贴的通知" in text
    assert "补贴标准为每辆新能源汽车补贴" in text


def test_extract_content_excludes_nav_footer_chrome():
    text = extract_content(_response())
    # Nav / footer chrome should not dominate the extracted body.
    assert "首页" not in text
    assert "版权所有" not in text


def test_trs_editor_wins_over_outer_container_and_excludes_scripts():
    response = HtmlResponse(
        url="https://example.gov.cn/policy.html",
        body="""<html><body><div id="main">
        <h1>通知</h1><script>function laiyuan(){}</script>
        <div class="TRS_Editor"><p>政策正文。</p>
        <script>tracking()</script><style>.hidden{display:none}</style></div>
        <div>相关链接和页面操作</div></div></body></html>""".encode(),
        encoding="utf-8",
    )
    assert extract_content(response).strip() == "政策正文。"
