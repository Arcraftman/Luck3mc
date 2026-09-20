"""Pipeline that mirrors crawled items into the FastAPI backend.

Disabled by default. Enable by setting, in ``config/*.yaml``:

    backend:
      ingest_url: "http://localhost:8000"
      ingest_token: "<shared token>"
      sink_enabled: true

The pipeline simply POSTs each item to ``<ingest_url>/api/ingest/policy``; the
backend stores it and broadcasts it over SSE so the Vue frontend updates live.
It never drops items and never raises — crawler behavior is unchanged when
disabled or when the backend is unreachable.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from crawler.utils.backend_connection import get_backend_ingest_token

_LOG = logging.getLogger(__name__)

_ITEM_FIELDS = (
    "title",
    "source_url",
    "pub_date",
    "pub_datetime",
    "doc_number",
    "category",
    "issuing_authority",
    "source_site",
    "content",
    "subsidy",
)


class BackendSinkPipeline:
    def __init__(self, ingest_url: str, token: str, enabled: bool) -> None:
        self.ingest_url = ingest_url.rstrip("/")
        self.token = token
        self.enabled = bool(self.ingest_url) and enabled
        self.failed = False

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            crawler.settings.get("BACKEND_INGEST_URL", "http://127.0.0.1:8000"),
            crawler.settings.get("BACKEND_INGEST_TOKEN") or get_backend_ingest_token(),
            crawler.settings.getbool("BACKEND_SINK_ENABLED", False),
        )

    def process_item(self, item, spider):
        if not self.enabled or self.failed:
            return item
        payload = {
            key: (bool(item.get(key, False)) if key == "subsidy" else item.get(key) or "")
            for key in _ITEM_FIELDS
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ingest_url}/api/ingest/policy",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Token": self.token,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status >= 400:
                    _LOG.warning("[backend_sink] ingest HTTP %s", resp.status)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            _LOG.warning("[backend_sink] ingest failed (%s): %s", self.ingest_url, exc)
            _LOG.warning("[backend_sink] disabling backend writes for the rest of this crawl")
            self.failed = True
        return item
