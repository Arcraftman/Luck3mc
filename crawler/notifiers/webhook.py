"""Generic HTTP webhook notifier.

Supports the common personal-WeChat push services out of the box:

* ``serverchan`` — Server酱 (sctapi.ftqq.com). Bind your personal WeChat by
  scanning a QR, then POST to ``https://sctapi.ftqq.com/<token>.send``.
* ``pushplus``   — pushplus.plus. Bind WeChat, POST to /send with your token.
* ``wecom``      — 企业微信 group robot webhook (qyapi.weixin.qq.com).
* ``generic``    — any endpoint that accepts a JSON body.

All payloads are JSON. Network failures are swallowed (return ``False``) so a
dead webhook never breaks the crawl.
"""

from __future__ import annotations

import json
import urllib.request

from .base import Notifier, NotifyMessage


class WebhookNotifier(Notifier):
    def __init__(
        self,
        url: str = "",
        kind: str = "generic",
        token: str = "",
        timeout: float = 10.0,
        template: str = "txt",
        _post=None,
    ):
        self.url = url
        self.kind = (kind or "generic").lower()
        self.token = token
        self.timeout = timeout
        # ``template`` selects the pushplus payload template. "txt" is the
        # default (backwards-compatible with the per-item notify pipeline);
        # "markdown" is used by scripts that push a formatted report.
        self.template = (template or "txt").lower()
        # ``_post`` is injectable for tests: (url, payload, headers) -> str
        self._post = _post or self._urllib_post

    # -- transport ---------------------------------------------------------
    def _urllib_post(self, url: str, payload: dict, headers: dict) -> str:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8", "replace")

    # -- endpoint + payload shaping ---------------------------------------
    def _endpoint(self) -> str:
        if self.kind == "serverchan":
            return f"https://sctapi.ftqq.com/{self.token}.send"
        if self.kind == "pushplus":
            return "https://www.pushplus.plus/send"
        return self.url

    def _payload(self, message: NotifyMessage) -> dict:
        text = message.render_text()
        if self.kind == "serverchan":
            return {"title": message.title[:64] or "新政策", "desp": text}
        if self.kind == "pushplus":
            return {
                "token": self.token,
                "title": message.title[:64] or "新政策",
                "content": text,
                "template": self.template,
            }
        if self.kind == "wecom":
            return {"msgtype": "text", "text": {"content": text}}
        return {
            "title": message.title,
            "url": message.url,
            "pub_date": message.pub_date,
            "source_site": message.source_site,
            "content": text,
        }

    # -- public ------------------------------------------------------------
    def send(self, message: NotifyMessage) -> bool:
        if not message.url:
            return False
        endpoint = self._endpoint()
        if not endpoint:
            return False
        try:
            self._post(
                endpoint,
                self._payload(message),
                {"Content-Type": "application/json; charset=utf-8"},
            )
            return True
        except Exception:  # noqa: BLE001 - never crash the crawl
            return False

    def send_markdown(self, title: str, content_md: str) -> bool:
        """Push a single Markdown report to WeChat (pushplus ``markdown`` template).

        ``title`` is clipped to 64 chars and falls back to "政策报告" when empty.
        Network/transport failures return ``False`` — this method never raises.
        """
        if self.kind != "pushplus":
            # Markdown rendering is only meaningful for pushplus; other backends
            # still attempt delivery but are not the target of this helper.
            return False
        endpoint = self._endpoint()
        if not endpoint:
            return False
        payload = {
            "token": self.token,
            "title": (title or "")[:64] or "政策报告",
            "content": content_md,
            "template": "markdown",
        }
        try:
            self._post(
                endpoint,
                payload,
                {"Content-Type": "application/json; charset=utf-8"},
            )
            return True
        except Exception:  # noqa: BLE001 - never crash the caller
            return False
