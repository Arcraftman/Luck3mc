"""Heuristic policy vs. news classifier for generic government-site crawling.

The :class:`crawler.spiders.gov_policy.root_spider.GovPolicyRootSpider` crawls
*every* link under a set of operator-provided URL roots (China-government /
Shanghai-government policy sections). It must keep **policy documents and
government files** but drop **current-affairs / political news** and skip pure
listing / index pages.

The heuristics below are intentionally conservative and *tunable*: they are
plain module-level lists so the operator can extend them without touching the
spider. A page is treated as a policy document only when it passes all of:

  1. not flagged as news (URL path / title keywords), and
  2. shows a positive policy signal (URL path fragment, a document-type title
     keyword such as 办法/通知/条例, or a body "印发/公布" marker), and
  3. carries enough body text to be an actual article (not a stub / nav page).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# News signals — pages matching these are NOT policy documents.
# ---------------------------------------------------------------------------
# URL path fragments that almost always denote news / media / activity pages.
NEWS_URL_PATH_FRAGMENTS: list[str] = [
    "/xinwen/",
    "/news/",
    "/yaowen/",
    "/mtbd/",      # 媒体百度和（media roundup）
    "/video/",
    "/shipin/",
    "/v_",
    "/tp/",        # 图片（图库）
    "/photo/",
    "/pic/",
    "/img/",
    "/cs/",        # 图片新闻常见前缀
]

# Title keywords that mark a news / activity / soft piece rather than a
# normative document.
NEWS_TITLE_KEYWORDS: list[str] = [
    "新闻",
    "快讯",
    "要闻",
    "报道",
    "记者",
    "视频",
    "直播",
    "图集",
    "图文",
    "访谈",
    "讲话",
    "致辞",
    "会见",
    "调研",
    "考察",
    "活动",
    "论坛",
    "展览",
    "招聘",
    "招考",
    "喜报",
]

# ---------------------------------------------------------------------------
# Policy signals — positive evidence that a page IS a policy / gov document.
# ---------------------------------------------------------------------------
# URL path fragments typical of policy / document sections.
POLICY_URL_PATH_FRAGMENTS: list[str] = [
    "/zhengce/",     # 政策（中国政府网）
    "/zhengcefabu/",  # 政策发布（财政部各司子站 gss/jrs/szs/sbs.mof.gov.cn）
    "/zhengcefagui/", # 政策法规（财政部经济建设司 jjs.mof.gov.cn）
    "/guizhangzhidu/",# 规章制度（财政部国库司 gks.mof.gov.cn）
    "/zcgz/",         # 政策工作（财政部综合司 zwgls.mof.gov.cn）
    "/tongzhigonggao/",# 通知公告（财政部经济建设司 jjs.mof.gov.cn）
    "/czpjzhengcefabu_2_2/", # 财政评价政策发布（农业农村司 nys.mof.gov.cn，混合大小写）
    "/zcfgk",         # 政策法规库（国家税务总局 fgk.chinatax.gov.cn）
    "/sscx/",         # 查询（12366 纳税服务平台）
    "/qykjzc/",       # 企业科技政策专区（科技部 most.gov.cn）
    "/gqrdw/",        # 高企认定栏目（高企认定管理工作网 innocom.gov.cn）
    "/art/",          # 政策文章栏目（国家政务服务平台 zc.gjzwfw.gov.cn/art）
    "/zxzc/",         # 政策性文件栏目（工业和信息化部 www.miit.gov.cn/xwfb/zxzc）
    "/zfwj",         # 政府文件
    "/xxgk/",        # 信息公开（已覆盖科技部 /xxgk/xinxifenlei/fdzdgknr 根）
    "/gkml/",        # 公开目录
    "/zcfg/",        # 政策法规
    "/fg/",          # 法规
    "/wb/",          # 公报
    "/zc/",          # 政策（缩写）
    "/policy/",
    "/policies/",
    "/tzcjd_",       # 政策解读栏目（包含政策问答）
    "/document",
    "/doc/",
    "/flfg/",        # 法律法规
    "/gongkai/",
    "/gk/",          # 公开
    "/content_",     # gov.cn 详情页标记（content_xxxx.htm）
    "/art_",         # 某些站点文章页
]

# Strong document-type title keywords — their presence alone is enough.
DOC_TITLE_KEYWORDS: list[str] = [
    "办法",
    "规定",
    "细则",
    "通知",
    "意见",
    "决定",
    "公告",
    "通告",
    "命令",
    "批复",
    "函",
    "令",
    "条例",
    "规划",
    "方案",
    "标准",
    "指引",
    "措施",
    "规范",
    "目录",
    "清单",
    "解释",
    "决议",
    "白皮书",
    "纲要",
    "指南",
    "规程",
    "暂行",
    "印发",
    "政策问答",
    "政策解读",
]

# Body markers that only appear inside a real normative document.
POLICY_BODY_MARKERS: list[str] = [
    "现印发",
    "现将",
    "印发给你们",
    "印发《",
    "特公布",
    "现公布",
    "予以公布",
    "现予公布",
    "现予公告",
    "经研究决定",
    "颁布",
    "自公布之日起",
    "施行",
]

# Generic (weak) title keywords — only count when corroborated by a URL
# policy fragment or a body marker, so that a listing page titled "政策文件"
# is not mistaken for a document.
WEAK_TITLE_KEYWORDS: list[str] = ["政策", "文件"]


def is_news(url: str, title: str) -> bool:
    """True when the page is clearly current-affairs / news, not a document."""
    u = (url or "").lower()
    t = title or ""
    if any(frag in u for frag in NEWS_URL_PATH_FRAGMENTS):
        return True
    if any(kw in t for kw in NEWS_TITLE_KEYWORDS):
        return True
    return False


def has_policy_signal(url: str, title: str, text: str) -> bool:
    """True when the page shows positive evidence of being a policy document."""
    u = (url or "").lower()
    t = title or ""
    if any(frag in u for frag in POLICY_URL_PATH_FRAGMENTS):
        return True
    if any(kw in t for kw in DOC_TITLE_KEYWORDS):
        return True
    if any(m in (text or "") for m in POLICY_BODY_MARKERS):
        return True
    # Weak title keyword needs corroboration from URL fragment or body marker.
    if any(kw in t for kw in WEAK_TITLE_KEYWORDS) and (
        any(frag in u for frag in POLICY_URL_PATH_FRAGMENTS)
        or any(m in (text or "") for m in POLICY_BODY_MARKERS)
    ):
        return True
    return False


def _strong_signal(url: str, title: str) -> bool:
    """A high-confidence policy signal that needs only a stub-length check.

    Either the URL sits in a policy/document section (``/zhengce/``, ``/xxgk/``…)
    or the title carries a document-type keyword (``办法`` / ``通知`` / ``条例``…).
    When this is present we keep the page even if the extracted body is short
    (some detail pages render their prose via JS and our extractor grabs little).
    """
    u = (url or "").lower()
    t = title or ""
    if any(frag in u for frag in POLICY_URL_PATH_FRAGMENTS):
        return True
    if any(kw in t for kw in DOC_TITLE_KEYWORDS):
        return True
    return False


def is_policy_document(
    url: str,
    title: str,
    text: str,
    *,
    min_content_len: int = 200,
) -> bool:
    """Decide whether a crawled page is a keepable policy / government document.

    Parameters
    ----------
    url, title, text:
        The page's URL, extracted title and main-body text.
    min_content_len:
        Minimum body length (chars) for pages that show only a *weak* policy
        signal (e.g. a generic "政策" title with no URL/body corroboration).
        Pages carrying a *strong* signal (policy URL section or a document-type
        title keyword) only need an 80-char stub check, because a real detail
        page can be short even when our extractor grabs little prose.
    """
    if is_listing_url(url) or is_news(url, title):
        return False
    doc_title = any(kw in (title or "") for kw in DOC_TITLE_KEYWORDS)
    detail = _looks_like_detail(url)
    # Section / listing pages (no file extension and a generic title) are not
    # documents even when their URL sits in a /zhengcefabu/ section — dropping
    # them avoids storing index pages as "policies".
    if not (doc_title or detail):
        return False
    strong = _strong_signal(url, title)
    if not strong and not has_policy_signal(url, title, text):
        return False
    threshold = 80 if strong else min_content_len
    return len((text or "").strip()) >= threshold


def is_listing_url(url: str) -> bool:
    """Recognise index/list endpoints even when titles contain 公告/通知."""
    from urllib.parse import urlparse

    path = urlparse(url).path.lower()
    basename = path.rsplit("/", 1)[-1]
    return (not basename or bool(re.match(
        r"(?:index|list|list_[\w-]+|index_\d+)(?:\.(?:s?html?|aspx?|jsp))?$", basename
    )) or basename in {"tzggmore", "main"})


# A real detail page ends in a document file extension, or carries a known
# detail-page URL hint (gov.cn content_/art_, or the mof `t2026..._xxxx.htm`
# pattern). Section / listing pages have none of these.
_DETAIL_EXT_RE = re.compile(
    r"\.(?:htm|html|shtml|asp|aspx|php|jsp)(?:[?#].*)?$", re.I
)
_DETAIL_HINTS = ("/content_", "/art_", "/t20")


def _looks_like_detail(url: str) -> bool:
    """True when the URL looks like a concrete document/detail page."""
    u = url or ""
    if _DETAIL_EXT_RE.search(u):
        return True
    if any(hint in u for hint in _DETAIL_HINTS):
        return True
    return False
