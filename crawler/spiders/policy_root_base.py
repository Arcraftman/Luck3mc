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
from scrapy.link import Link
from scrapy.spiders import CrawlSpider, Rule

from crawler.items import TaxPolicyItem
from crawler.utils.compliance import is_compliance_blocked
from crawler.utils.loaders import build_loader
from crawler.utils.policy_classify import (
    NEWS_URL_PATH_FRAGMENTS,
    is_policy_document,
    is_listing_url,
)
from crawler.utils.policy_parse import (
    extract_content,
    extract_doc_number,
    extract_issuing_authority,
    extract_pub_date,
    extract_pub_datetime,
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

    # Do not even schedule links whose URL clearly identifies a pre-2026
    # archive or document. The DateFilterPipeline remains the authoritative
    # check because some sites omit the publication year from their URLs.
    earliest_publication_year = 2026

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
        # Don't spam WeChat per-item; the daily report is the WeChat channel.
        "NOTIFY_ENABLED": False,
        "DEFAULT_REQUEST_HEADERS": {"Accept-Language": "zh-CN,zh;q=0.9"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, roots: str | None = None, *args, **kwargs):
        # 注意：Scrapy 的 Spider 基类自带只读 property `logger`
        # （返回 logging.getLogger(self.name)），不能用 `self.logger = ...` 赋值。
        # 直接 self.logger 即可，无需初始化。

        # Resolve roots BEFORE super().__init__ so CrawlSpider._compile_rules()
        # sees the assembled ``self.rules``.
        self._roots = self._resolve_roots(roots)
        if not self._roots:
            raise CloseSpider(reason="no_roots_configured")

        self.allowed_domains = sorted({r["domain"] for r in self._roots})
        self.start_urls = [url for r in self._roots for url in r.get("start_urls", [r["url"]])]
        self.blocked_domains = set()
        self._known_documents = set()
        self._public_paths = {r["domain"]: r["allow_paths"] for r in self._roots
                              if r.get("allow_paths")}
        self._detail_paths = {r["domain"]: r["detail_paths"] for r in self._roots
                              if r.get("detail_paths")}
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
                **{key: r[key] for key in ("start_urls", "allow_paths", "detail_paths", "pagination")
                   if key in r},
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
        self._load_known_documents()
        for url in self.start_urls:
            req = Request(url, dont_filter=True)
            if self._domain_of(url) in self._js_domains:
                req.meta["playwright"] = True
            yield req

    def _load_known_documents(self):
        """Read the existing ledger once; never query the DB per discovered link."""
        self._known_documents.clear()
        if not self.crawler.settings.getbool("INCREMENTAL_CRAWL_ENABLED", True):
            return
        database_url = self.crawler.settings.get("DATABASE_URL")
        if not database_url:
            return
        from sqlalchemy import select
        from crawler.db.models import CrawledUrl
        from crawler.db.session import get_engine

        engine = None
        try:
            engine = get_engine(database_url)
            with engine.connect() as connection:
                rows = connection.execute(select(CrawledUrl.url, CrawledUrl.source_site).where(
                    CrawledUrl.source_site.in_(set(self._domain_to_site.values()))
                ))
                self._known_documents = {(url, site) for url, site in rows}
            self.crawler.stats.set_value("incremental/known_documents", len(self._known_documents))
            self.logger.info("[incremental] 已加载 %d 条历史记录，下载前跳过已采集详情，继续扫描列表。",
                             len(self._known_documents))
        except Exception:
            # A missing/unavailable ledger must never prevent discovery.
            self.logger.warning("[incremental] 无法读取历史记录，本次回退到完整扫描。")
            self.crawler.stats.inc_value("incremental/ledger_unavailable")
        finally:
            if engine is not None:
                engine.dispose()

    def _already_collected(self, url):
        if url in self.start_urls or is_listing_url(url):
            return False
        domain = self._domain_of(url)
        patterns = self._detail_paths.get(domain)
        if patterns and not any(re.search(p, urlparse(url).path) for p in patterns):
            return False
        return (url, self._domain_to_site.get(domain, self.source_site or self.category)) in self._known_documents

    def process_request(self, request, response):
        """Reject explicit old archives, then tag JS-only requests."""
        # Details should not recursively lead into navigation/related articles.
        patterns = self._detail_paths.get(self._domain_of(response.url), [])
        if any(re.search(pattern, urlparse(response.url).path) for pattern in patterns):
            return None
        if not self.is_public_url(request.url):
            return None
        if self._already_collected(request.url):
            self.crawler.stats.inc_value("incremental/skipped_known_detail")
            return None
        if self._is_explicitly_old_url(request.url):
            self.crawler.stats.inc_value("request_filter/dropped_pre_2026_url")
            return None
        if self._domain_of(request.url) in self._js_domains:
            request.meta["playwright"] = True
        return request

    def _requests_to_follow(self, response):
        yield from super()._requests_to_follow(response)
        if not isinstance(response, HtmlResponse):
            return
        # Some static archives expose their page count only in a JS widget.
        # Discover sibling pages from the configured entry, without executing JS.
        for root in self._roots:
            pagination = root.get("pagination")
            if not pagination or response.url not in root.get("start_urls", []):
                continue
            match = re.search(pagination["total_pattern"], response.text)
            if not match:
                continue
            total_pages = int(match.group(1))
            default_limit = int(pagination.get("max_pages", total_pages))
            settings = getattr(self.crawler, "settings", None)
            configured_limit = (
                settings.getint("INCREMENTAL_ARCHIVE_PAGE_LIMIT", default_limit)
                if settings is not None else default_limit
            )
            max_pages = total_pages if configured_limit <= 0 else configured_limit
            scheduled_pages = min(total_pages, max_pages)
            if scheduled_pages < total_pages:
                self.crawler.stats.inc_value(
                    "incremental/skipped_archive_pages", total_pages - scheduled_pages
                )
                self.logger.info(
                    "[incremental] %s 共 %d 页，本次只扫描最新 %d 页。",
                    response.url, total_pages, scheduled_pages,
                )
            for page in range(2, scheduled_pages + 1):
                url = response.urljoin(pagination["template"].format(page=page))
                request = self._build_request(0, Link(url))
                # Newer archive pages and document details run before old pages.
                request.priority = -page
                request = self.process_request(request, response)
                if request is not None:
                    yield request

    # ------------------------------------------------------------------ #
    def process_links(self, links):
        """Drop external, news, and explicit pre-2026 links before scheduling."""
        kept = []
        for link in links:
            if not self.is_public_url(link.url):
                continue
            netloc = self._domain_of(link.url)
            if netloc and netloc not in self.allowed_domains:
                continue
            if any(frag in link.url.lower() for frag in NEWS_URL_PATH_FRAGMENTS):
                continue
            if self._is_explicitly_old_url(link.url):
                self.crawler.stats.inc_value("request_filter/dropped_pre_2026_url")
                continue
            kept.append(link)
        return kept

    def is_public_url(self, url):
        domain = self._domain_of(url)
        if domain in self.blocked_domains:
            return False
        patterns = self._public_paths.get(domain)
        return not patterns or any(re.search(p, urlparse(url).path) for p in patterns)

    def block_site(self, requested_url, final_url=None):
        domain = self._domain_of(requested_url)
        if domain not in self.blocked_domains:
            self.blocked_domains.add(domain)
            self.crawler.stats.inc_value(f"site_guard/blocked/{domain}")
            self.logger.warning("[site-guard] 暂停本站，其他来源继续: %s -> %s",
                                domain, final_url or requested_url)

    def _is_explicitly_old_url(self, url: str) -> bool:
        """Whether a URL clearly belongs to an archive before 2026.

        Government sites commonly encode years as ``/2025/``, ``/202509/``
        or suffixes such as ``qtwj2014``. If multiple years occur, use the
        newest one so a 2026 document referring to an older law is retained.
        URLs without a recognisable year must still be fetched and verified
        from their publication metadata by ``DateFilterPipeline``.
        """
        path = urlparse(url).path
        standalone = [int(value) for value in re.findall(
            r"(?<!\d)((?:19|20)\d{2})(?!\d)", path
        )]
        compact = [int(value) for value in re.findall(
            r"(?<!\d)((?:19|20)\d{2})\d{2}(?:\d{2})?(?!\d)", path
        )]
        years = standalone + compact
        return bool(years) and max(years) < self.earliest_publication_year

    def parse_page(self, response):
        """Classify and extract a visited page as a policy document (or skip)."""
        if not isinstance(response, HtmlResponse):
            return

        if self._domain_of(response.url) in self.blocked_domains:
            return
        if is_compliance_blocked(response.text or "", response.status):
            self.block_site(response.url)
            return

        patterns = self._detail_paths.get(self._domain_of(response.url))
        if patterns and not any(re.search(p, urlparse(response.url).path) for p in patterns):
            return

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

        pub_datetime = extract_pub_datetime(response)
        if pub_datetime:
            loader.add_value("pub_datetime", pub_datetime)
        pub_date = pub_datetime[:10] if pub_datetime else extract_pub_date(response)
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
