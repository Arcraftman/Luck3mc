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

from crawler.utils.config_loader import load_config

_LOG = logging.getLogger(__name__)

_ITEM_FIELDS = (
    "title",
    "source_url",
    "pub_date",
    "issuing_authority",
    "source_site",
    "content",
    "subsidy",
)


class BackendSinkPipeline:
    def __init__(self) -> None:
        cfg = (load_config().get("backend") or {}) if load_config() else {}
        self.ingest_url = (cfg.get("ingest_url") or "").rstrip("/")
        self.token = cfg.get("ingest_token") or ""
        self.enabled = bool(self.ingest_url) and bool(cfg.get("sink_enabled"))

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider):
        if not self.enabled:
            return item
        payload = {k: item.get(k) for k in _ITEM_FIELDS}
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    _LOG.warning("[backend_sink] ingest HTTP %s", resp.status)
        except urllib.error.URLError as exc:
            _LOG.warning("[backend_sink] ingest failed (%s): %s", self.ingest_url, exc)
        return item
