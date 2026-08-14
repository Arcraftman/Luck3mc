"""Integration test: a new item flows through NotifyPipeline to a webhook.

Spins up a local HTTP server that records any POST body, points the
notifier at it, feeds a synthetic item, and asserts the webhook received the
new URL. This proves the monitor -> notify loop end-to-end without touching
the network.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler.pipelines.notify import NotifyPipeline
from scrapy.settings import Settings


class _RecordHandler(BaseHTTPRequestHandler):
    received: list[str] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", "replace")
        _RecordHandler.received.append(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):  # silence test server logs
        pass


def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class _FakeSpider:
    source_site = "test.gov.cn"

    @property
    def logger(self):
        import logging
        return logging.getLogger("test_spider")


def test_notify_pipeline_posts_to_webhook():
    port = _free_port()
    _RecordHandler.received = []
    server = ThreadingHTTPServer(("127.0.0.1", port), _RecordHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        settings = Settings()
        settings.set("NOTIFY_ENABLED", True)
        settings.set("NOTIFY_BACKEND", "webhook")
        settings.set("NOTIFY_WEBHOOK_URL", f"http://127.0.0.1:{port}/notify")
        settings.set("NOTIFY_WEBHOOK_KIND", "generic")
        settings.set("DATABASE_URL", "")  # in-memory dedup; all items are "new"

        pipeline = NotifyPipeline(settings)
        pipeline.open_spider(_FakeSpider())

        item = {
            "title": "高新技术企业认定管理办法",
            "source_url": "https://www.innocom.gov.cn/xx/123.html",
            "pub_date": "2026-03-01",
            "source_site": "innocom.gov.cn",
        }
        pipeline.process_item(item, _FakeSpider())

        assert len(_RecordHandler.received) == 1
        payload = json.loads(_RecordHandler.received[0])
        assert payload["url"] == "https://www.innocom.gov.cn/xx/123.html"
        assert "高新技术企业认定管理办法" in payload["content"]
    finally:
        server.shutdown()
