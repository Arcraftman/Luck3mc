"""Site-agnostic helpers for crawling Chinese government policy pages.

Every spider in this project is thin: it declares its start URLs, the
``allowed_domains``, a list of regexes that match *detail* links, and which
item class to emit. All the messy normalisation — title cleanup, finding the
main content container, pulling the publish date / document number /
issuing authority out of loosely-structured HTML — lives here and is shared.

Government policy sites share enough structure that a layered, "try several
selectors and keep the best" strategy works across most of them without
per-site bespoke code. Sites that render their lists with JavaScript (Layui
tables, SPAs) cannot be parsed from static HTML and need a headless download
handler instead — see ``crawler/downloaders/playwright.py``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from urllib.parse import urljoin

_DATE_RE = re.compile(
    r"(20\d{2})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})"
)
_DOC_NUM_RE = re.compile(r"[〔【\[]?\s*(20\d{2})\s*[〕】\]]\s*\d+\s*号")
_AUTHORITY_RE = re.compile(
    r"(?:发文机关|发布机关|制定机关|发文单位)[：:]\s*([^\n<]{2,40})"
)
# Strip the trailing " - 中华人民共和国XXX" / "_ 国家税务总局" site suffix.
_TITLE_SUFFIX_RE = re.compile(
    r"\s*[-—_|]\s*(中华人民共和国.{0,20}|国家税务总局.{0,20}|"
    r".{0,12}政府.{0,8}|.{0,10}部.{0,8}|.{0,12}委员会.{0,8})\s*$",
    re.S,
)

# Content containers, scored by extracted text length (most text wins).
_CONTENT_CONTAINERS = [
    ".TRS_Editor",
    ".trs_editor_view",
    ".xxgk_detail_content",
    ".article",
    ".article_con",
    ".article_text",
    "#content",
    ".content",
    ".main",
    "#main",
    ".pages_content",
    ".con_txt",
    ".v_news_content",
    ".detail",
    ".news_con",
    ".text",
    ".zcwj",
    ".chapter-content",
    ".rich_media_content",
    ".article-body",
    ".entry-content",
    ".article-detail",
]


def iter_detail_links(
    response,
    patterns: Iterable[re.Pattern[str]],
    min_title_len: int = 8,
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(absolute_url, title, date_str)`` for anchors matching any pattern.

    The date is sniffed from the link's containing ``<li>`` / ``<tr>`` so list
    pages that print the date next to the title still get a publish date even
    when the detail page is JS-heavy.
    """
    sel = response.selector
    for a in sel.css("a[href]"):
        href = a.attrib.get("href", "")
        if not href:
            continue
        title = " ".join(a.css("::text").getall()).strip()
        if len(title) < min_title_len:
            continue
        if not any(p.search(href) for p in patterns):
            continue
        row = a.xpath("./ancestor::li[1] | ./ancestor::tr[1] | ./parent::*")
        row_text = " ".join(row.css("::text").getall()) if row else ""
        date_match = _DATE_RE.search(row_text)
        yield (
            urljoin(response.url, href),
            title,
            date_match.group(0) if date_match else "",
        )


def find_next_page(
    response, labels: tuple[str, ...] = ("下一页", "下页", "下一页>", "next", "»")
) -> str | None:
    """Return the absolute URL of a pagination 'next' link, if present."""
    sel = response.selector
    for a in sel.css("a[href]"):
        label = " ".join(a.css("::text").getall()).strip()
        if any(lb in label for lb in labels):
            return urljoin(response.url, a.attrib.get("href", ""))
    return None


def extract_title(response) -> str:
    """Best-effort title: ``<h1>`` → common heading classes → cleaned ``<title>``."""
    for selector in (
        "h1::text",
        "h2::text",
        ".xxgk_title::text",
        ".article_title::text",
        ".title::text",
        ".bt::text",
    ):
        value = response.css(selector).get()
        if value and value.strip():
            return " ".join(value.split())
    raw = response.css("title::text").get() or ""
    raw = " ".join(raw.split())
    return _TITLE_SUFFIX_RE.sub("", raw).strip()


def _container_xpath(spec: str) -> str:
    """把 ``.class`` / ``#id`` 选择器转为等价 XPath。

    部分政府详情页（如中国政府网 gov.cn）的 HTML 结构会让 cssselect 在深层
    div 上失效——``response.css('.pages_content')`` 返回 0，但 ``//div`` 能找到，
    且正文容器有时被 lxml 解析到 ``<body>`` 子树之外（``//body//text()`` 也取不到）。
    因此内容容器改用 XPath 选取：对结构正常的页面与原 CSS 等价，又能救回这类坏
    结构页面。
    """
    if spec.startswith("#"):
        raw = spec[1:]
        # 简单安全的字面量包裹（id 通常不含引号，这里做最小防护）。
        if "'" not in raw:
            lit = f"'{raw}'"
        elif '"' not in raw:
            lit = f'"{raw}"'
        else:
            lit = "concat('" + raw.replace("'", "',\"'\",'") + "')"
        return f"//*[@id={lit}]"
    token = spec[1:] if spec.startswith(".") else spec
    return (
        "//*[contains(concat(' ', normalize-space(@class), ' '), "
        f"' {token} ')]"
    )


def extract_content(response) -> str:
    """Return the main article body, scoring candidate containers by length."""
    # TRS editor marks the article itself; outer #main/.content containers
    # often include controls, related links and inline JavaScript.
    text_path = ".//text()[not(ancestor::script) and not(ancestor::style)]"
    editors = response.xpath(_container_xpath(".TRS_Editor"))
    if editors:
        editor = max(editors, key=lambda node: len("".join(node.xpath(text_path).getall())))
        text = "\n".join(line for line in editor.xpath(text_path).getall() if line.strip())
        if text.strip():
            return text
    best_node = None
    best_len = 0
    for spec in _CONTENT_CONTAINERS:
        for node in response.xpath(_container_xpath(spec)):
            text = " ".join(node.xpath(text_path).getall())
            if len(text) > best_len:
                best_node, best_len = node, len(text)
    if best_node is not None:
        return "\n".join(
            line for line in best_node.xpath(text_path).getall() if line.strip()
        )
    # Fallback: every <p> in the document (nav/footer text is usually not <p>).
    # 用 //p 而非 body p——规避部分页面正文不在 body 子树下的情况（如 gov.cn）。
    return "\n".join(
        line for line in response.xpath("//p//text()").getall() if line.strip()
    )


def _normalise_date(match: re.Match[str]) -> str:
    return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def extract_pub_datetime(response) -> str | None:
    """Read publication metadata/labels only; never infer time from body dates."""
    from crawler.utils.publication_time import parse_publication_time

    candidates = []
    for node in response.css("meta"):
        key = (node.attrib.get("name") or node.attrib.get("property")
               or node.attrib.get("http-equiv") or "").lower()
        if key in {"pubdate", "publishdate", "publish_date", "date",
                   "article:published_time"}:
            candidates.append(node.attrib.get("content", ""))
    # Script/style dates and dates inside policy clauses are not publication times.
    text = " ".join(response.xpath(
        "//body//text()[not(ancestor::script) and not(ancestor::style)]"
    ).getall())
    candidates.extend(re.findall(
        r"(?:发布时间|发布日期|发布于)\s*[：:]?\s*"
        r"(20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}日?"
        r"[T\s]+\d{1,2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)", text
    ))
    for candidate in candidates:
        timestamp = parse_publication_time(candidate)
        if timestamp is not None:
            return timestamp.isoformat()
    return None


def extract_pub_date(response) -> str | None:
    """Publish date from meta tags first, then a date appearing in the body."""
    for meta in (
        'meta[name="pubdate"]::attr(content)',
        'meta[name="publishdate"]::attr(content)',
        'meta[name="publish_date"]::attr(content)',
        'meta[http-equiv="Date"]::attr(content)',
        'meta[property="article:published_time"]::attr(content)',
    ):
        value = response.css(meta).get()
        if value:
            m = _DATE_RE.search(value)
            if m:
                return _normalise_date(m)
    body = " ".join(response.css("body ::text").getall())
    m = _DATE_RE.search(body)
    return _normalise_date(m) if m else None


def extract_doc_number(response) -> str | None:
    """e.g. 〔2026〕12号 / [2026]34号."""
    body = " ".join(response.css("body ::text").getall())
    m = _DOC_NUM_RE.search(body)
    return m.group(0).replace(" ", "") if m else None


def extract_issuing_authority(response) -> str | None:
    """Issuing authority from a '发文机关：XXX' label, if present."""
    body = " ".join(response.css("body ::text").getall())
    m = _AUTHORITY_RE.search(body)
    return m.group(1).strip() if m else None
