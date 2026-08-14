"""Offline end-to-end test: run a *real* config-driven category spider.

No network access required. A throwaway ``http.server`` serves a tiny link
chain:

    /                          -> tiny page linking to the list fixture
    /most_qykjzc_list.html    -> real MOST *list* fixture (relative
                                 ``../../xxgk/...`` links)
    /xxgk/...                 -> real MOST *detail* fixture

We start the real ``gaoqi`` spider — a subclass of :class:`PolicyRootBaseSpider`
that reads its roots from ``gov_categories.yaml`` — at the fixture directory via
the ``roots=`` command-line override (which bypasses the YAML and points the
spider at ``http://127.0.0.1:<port>/``). The list page's relative links resolve
in-subtree to ``/xxgk/...``, which the spider follows and parses through the full
pipeline (spider -> ItemLoader cleaning -> validation -> de-duplication -> item
collection). Because the ``/xxgk/`` URLs carry the policy URL fragment,
:func:`is_policy_document` accepts them and the spider yields items.

The spider's own ``custom_settings`` (politeness: ROBOTSTXT_OBEY, delay,
CLOSESPIDER_PAGECOUNT, …) are overridden *on the class* for this harness — that
is the only priority that beats ``custom_settings`` (spider > command > project),
so a plain ``settings.set(..., priority="command")`` cannot touch them.
"""

import http.server
import socket
import threading
from pathlib import Path

import pytest
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from crawler.spiders.gov_categories import GaoqiSpider

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
COLLECTED = []


class CollectPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        COLLECTED.append(item)
        return item


class _FixtureHandler(http.server.BaseHTTPRequestHandler):
    """Serve a tiny link chain that exercises the full crawl path.

    ``/`` links to the real MOST *list* fixture; that list's relative
    ``../../xxgk/...`` links resolve to ``/xxgk/...``, which we answer with the
    MOST *detail* fixture. The ``/xxgk/`` URLs carry the policy URL fragment,
    so :func:`is_policy_document` accepts them and the spider yields items.
    """

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            body = b'<html><body><a href="/most_qykjzc_list.html">list</a></body></html>'
        elif p == "/most_qykjzc_list.html":
            body = (FIXTURES / "most_qykjzc_list.html").read_bytes()
        elif "/xxgk/" in p:
            body = (FIXTURES / "most_qykjzc_detail.html").read_bytes()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.offline
def test_gaoqi_spider_end_to_end():
    COLLECTED.clear()
    port = _free_port()
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), _FixtureHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    # The spider's own ``custom_settings`` carry the project's politeness knobs
    # (ROBOTSTXT_OBEY, DOWNLOAD_DELAY, CLOSESPIDER_PAGECOUNT, …) at Scrapy's
    # *highest* priority ("spider" = 30). That outranks both "command" (20) and
    # "project" (10), so a plain ``settings.set(..., priority="command")`` cannot
    # touch them — and priority-merged dicts (ITEM_PIPELINES, …) would only get
    # partially overwritten. The only reliable way to make this ephemeral fixture
    # crawl fast and deterministic is to override the whole block *on the class*.
    orig_custom = dict(GaoqiSpider.custom_settings)
    GaoqiSpider.custom_settings = {
        **orig_custom,
        "ROBOTSTXT_OBEY": False,            # no robots.txt round-trip on 127.0.0.1
        "DOWNLOAD_DELAY": 0,
        "RANDOMIZE_DOWNLOAD_DELAY": 0,
        "AUTOTHROTTLE_ENABLED": False,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
        "CLOSESPIDER_PAGECOUNT": 250,       # generous: reach the /xxgk/ details
        "DEPTH_LIMIT": 2,                   # don't descend into detail-page assets
        "LOG_LEVEL": "ERROR",
        "OUTPUT_DIR": "data/test_output",
        # The fixture runs on 127.0.0.1:<random-port>; OffsiteMiddleware matches
        # on bare hostname and would reject the ported domain. Production spiders
        # use real, port-less domains where offsite works fine, so disable it here.
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware": None
        },
        # A minimal, deterministic pipeline: clean -> de-duplicate -> collect.
        # (The project's notify / JSONL-export pipelines are omitted so the test
        # has no side effects beyond the in-memory COLLECTED list.)
        "ITEM_PIPELINES": {
            "crawler.pipelines.validation.ValidationPipeline": 100,
            "crawler.pipelines.deduplication.DeduplicatePipeline": 200,
            "tests.integration.test_spiders.CollectPipeline": 300,
        },
    }

    try:
        settings = get_project_settings()
        process = CrawlerProcess(settings)
        # Start the spider at the fixture *directory* (trailing slash -> allow
        # regex ``^.../.*``) so the list fixture's ``../../xxgk/`` links are
        # in-subtree and get followed. ``roots=`` overrides the YAML block; the
        # spider still applies its classify / compliance machinery.
        process.crawl("gaoqi", roots=f"{base}/")
        process.start()
    finally:
        httpd.shutdown()
        GaoqiSpider.custom_settings = orig_custom

    assert len(COLLECTED) >= 1, f"expected >=1 item, got {len(COLLECTED)}"
    first = dict(COLLECTED[0])
    assert first.get("title"), "item title was empty"
    # The MOST <title> carries a " - 中华人民共和国科学技术部" suffix that the
    # parser must strip.
    assert "中华人民共和国科学技术部" not in first["title"]
    assert first.get("source_url", "").startswith("http")
    # The detail fixture carries a publish date -> should be normalised.
    assert first.get("pub_date"), "publish date not extracted"
    # category is carried from the subclass, not from the ad-hoc roots override.
    assert first.get("category") == "gaoqi"
