"""Config-driven base spider for government-policy root sweeps.

This replaces the earlier per-site spiders whose list / detail / auth logic was
hard-coded for each domain. Here *nothing* about a specific website lives in
Python: every root URL, allowed domain and category is declared in
``gov_categories.yaml``. A subclass only sets ``name`` and ``category``; all
crawling machinery — CrawlSpider rules, the compliance guard, the
policy-vs-news classifier, item extraction and the politeness settings — is
inherited.

That is the decoupling the project asked for:

* to add a website ........ edit YAML, not Python (no code change, no redeploy
  of logic, just config),
* to add a whole category .. add a YAML block plus a ~4-line subclass,
* no spider contains a ``.gov.cn`` / ``.chinatax.gov.cn`` / ``.mof.gov.cn``
  literal — the unit test ``test_no_hardcoded_domains`` enforces this.

Run
---
    scrapy crawl caishui                 # one category (reads its YAML block)
    scrapy crawl gov_policy_root         # the generic / local-gov block
    scrapy crawl caishui -a roots=https://x.gov.cn/zhengce/   # ad-hoc override

Why a single Rule
-----------------
``rules`` are assembled in ``__init__`` (before ``super().__init__``) from the
resolved roots: each root contributes one ``allow`` path-prefix regex so the
spider only descends into that root's subtree, on that root's domain. Listing
/ index pages are dropped by :func:`crawler.utils.policy_classify.is_policy_document`
(not a detail page, no document title), and news sections are excluded via the
``deny`` list.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import yaml
from scrapy.exceptions import CloseSpider
from scrapy.http import HtmlResponse, Request
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from crawler.items import TaxPolicyItem
from crawler.utils.compliance import is_compliance_blocked
from crawler.utils.loaders import build_loader
from crawler.utils.policy_classify import (
    NEWS_URL_PATH_FRAGMENTS,
    is_policy_document,
)
from crawler.utils.policy_parse import (
    extract_content,
    extract_doc_number,
    extract_issuing_authority,
    extract_pub_date,
    extract_title,
)

# Single source of truth for every root URL / domain / category.
DEFAULT_CONFIG_FILE = Path(__file__).resolve().parent / "gov_categories.yaml"


class PolicyRootBaseSpider(CrawlSpider):
    """Generic, fully config-driven government-policy crawler.

    Contract for subclasses
    ------------------------
    * set ``category`` (the key under ``gov_categories.yaml: categories``),
    * optionally set ``name`` (defaults to the category when omitted),
    * set nothing else — behaviour, settings and the actual URLs are inherited.
    """

    # Subclasses fill this in; the base resolves roots from the YAML block.
    category: str = ""

    # Fallback tag written when a visited domain has no explicit root name.
    source_site: str = ""

    # Politeness + safety. A broad sweep must stay gentle and bounded, and the
    # same knobs apply to every category spider, so they live here — not copied
    # into each subclass (that duplication was the old "hard-coded" smell).
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 2.0,
        "RANDOMIZE_DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "DEPTH_LIMIT": 5,
        "CLOSESPIDER_PAGECOUNT": 3000,   # hard stop so a sweep can't run forever
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
        # Keep historical policies under the root (don't restrict to "today").
        "CRAWL_TODAY_ONLY": False,
        # Don't spam WeChat per-item; the daily report is the WeChat channel.
        "NOTIFY_ENABLED": False,
        "DEFAULT_REQUEST_HEADERS": {"Accept-Language": "zh-CN,zh;q=0.9"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, roots: str | None = None, *args, **kwargs):
        # Resolve roots BEFORE super().__init__ so CrawlSpider._compile_rules()
        # sees the assembled ``self.rules``.
        self._roots = self._resolve_roots(roots)
        if not self._roots:
            raise CloseSpider(reason="no_roots_configured")

        self.allowed_domains = sorted({r["domain"] for r in self._roots})
        self.start_urls = [r["url"] for r in self._roots]
        # domain -> stable source_site label (from the YAML root name).
        self._domain_to_site = {
            r["domain"]: r.get("name", self.source_site or self.category)
            for r in self._roots
        }
        # Domains whose pages are JS-rendered (12366, zjtx, ...). Their requests
        # carry meta["playwright"] so the optional scrapy-playwright download
        # handler serves them. Driven entirely by the `js: true` flag in YAML —
        # no hard-coded domain here (decoupling contract).
        self._js_domains = {r["domain"] for r in self._roots if r.get("js")}

        allow = [self._path_allow(r["url"]) for r in self._roots]
        deny = list(NEWS_URL_PATH_FRAGMENTS)  # never descend into news sections
        self.rules = (
            Rule(
                LinkExtractor(
                    allow=allow,
                    deny=deny,
                    allow_domains=self.allowed_domains,
                    unique=True,
                ),
                callback="parse_page",
                follow=True,
                process_links="process_links",
                process_request="process_request",
            ),
        )
        super().__init__(*args, **kwargs)

    # ------------------------------------------------------------------ #
    def _resolve_roots(self, roots: str | None) -> list[dict]:
        """Build the root list from ``-a roots=`` (override) or the YAML block."""
        # 1) ad-hoc command-line override — bypasses the YAML entirely.
        if roots:
            out: list[dict] = []
            for raw in str(roots).split(","):
                url = raw.strip()
                if not url:
                    continue
                p = urlparse(url)
                if not p.netloc:
                    continue
                out.append({
                    "name": p.netloc.replace(".", "_"),
                    "url": url,
                    "domain": p.netloc,
                    "js": False,
                })
            if out:
                return out
        # 2) the matching category block in gov_categories.yaml.
        return self._load_yaml_roots()

    def _load_yaml_roots(self) -> list[dict]:
        if not self.category:
            self.logger.error("子类未设置 category，无法从 YAML 解析 roots")
            return []
        if not DEFAULT_CONFIG_FILE.exists():
            self.logger.error("配置文件不存在: %s", DEFAULT_CONFIG_FILE)
            return []
        try:
            with DEFAULT_CONFIG_FILE.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:  # noqa: BLE001
            self.logger.error("解析 gov_categories.yaml 失败: %s", exc)
            return []
        block = (data.get("categories") or {}).get(self.category)
        if not block:
            self.logger.error(
                "gov_categories.yaml 中找不到 category=%r 的配置块", self.category
            )
            return []
        resolved: list[dict] = []
        for r in block.get("roots") or []:
            url = (r.get("url") or "").strip()
            if not url:
                continue
            p = urlparse(url)
            if not p.netloc:
                continue
            resolved.append({
                "name": r.get("name") or p.netloc.replace(".", "_"),
                "url": url,
                "domain": r.get("domain") or p.netloc,
                "js": bool(r.get("js")),
            })
        return resolved

    @staticmethod
    def _path_allow(url: str) -> str:
        """Regex matching the root URL and every sub-path under it, any scheme.

        Scheme-agnostic (``https?``) so an ``http://`` start URL that 30x-
        redirects to ``https://`` still matches its own subtree.

        ``https://www.gov.cn/zhengce/`` -> ``^https?://www\\.gov\\.cn/zhengce/.*``
        ``https://www.gov.cn/zhengce``  -> ``^https?://www\\.gov\\.cn/zhengce(/.*)?$``
        """
        p = urlparse(url)
        base = f"{p.netloc}{p.path}"
        escaped = re.escape(base)
        if base.endswith("/"):
            return r"^https?://" + escaped + ".*"
        return r"^https?://" + escaped + r"(/.*)?$"

    @staticmethod
    def _domain_of(url: str) -> str:
        return urlparse(url).netloc

    # ------------------------------------------------------------------ #
    # Playwright (JS-rendered lists): config-driven, never hard-coded.
    # ------------------------------------------------------------------ #
    async def start(self):
        """Initial requests carry the playwright flag for JS-only domains.

        Scrapy 2.13+ drives spiders via an async ``start()`` generator; the old
        ``start_requests`` / ``make_requests_from_url`` hooks are gone. We only
        deviate from the default loop to tag JS-rendered roots (those flagged
        ``js: true`` in YAML) with ``meta["playwright"]`` so the optional
        scrapy-playwright download handler serves them.
        """
        for url in self.start_urls:
            req = Request(url, dont_filter=True)
            if self._domain_of(url) in self._js_domains:
                req.meta["playwright"] = True
            yield req

    def process_request(self, request, response):
        """Rule-followed links on JS-only domains also need Playwright."""
        if self._domain_of(request.url) in self._js_domains:
            request.meta["playwright"] = True
        return request

    # ------------------------------------------------------------------ #
    def process_links(self, links):
        """Drop external links and obvious news paths before enqueuing."""
        kept = []
        for link in links:
            netloc = self._domain_of(link.url)
            if netloc and netloc not in self.allowed_domains:
                continue
            if any(frag in link.url.lower() for frag in NEWS_URL_PATH_FRAGMENTS):
                continue
            kept.append(link)
        return kept

    def parse_page(self, response):
        """Classify and extract a visited page as a policy document (or skip)."""
        if not isinstance(response, HtmlResponse):
            return

        if is_compliance_blocked(response.text or ""):
            self.logger.warning("[合规守卫] 命中反爬页，停止: %s", response.url)
            raise CloseSpider(reason="waf_blocked_compliance")

        url = response.url
        title = extract_title(response)
        text = extract_content(response)

        if not is_policy_document(url, title, text):
            return

        loader = build_loader(TaxPolicyItem(), response)
        loader.add_value(
            "source_site",
            self._domain_to_site.get(
                self._domain_of(url), self.source_site or self.category
            ),
        )
        loader.add_value("category", self.category)
        loader.add_value("source_url", url)
        loader.add_value("title", title)
        loader.add_value("content", text)

        pub_date = extract_pub_date(response)
        if pub_date:
            loader.add_value("pub_date", pub_date)
        doc_number = extract_doc_number(response)
        if doc_number:
            loader.add_value("doc_number", doc_number)
        authority = extract_issuing_authority(response)
        if authority:
            loader.add_value("issuing_authority", authority)

        item = loader.load_item()
        self.logger.info("[policy] 命中政策文档: %s", title)
        yield item
