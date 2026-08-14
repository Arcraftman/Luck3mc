"""Unit tests for :meth:`crawler.notifiers.webhook.WebhookNotifier.send_markdown`.

Injects a fake ``_post`` so no network call is made; asserts the pushplus
payload carries ``template=markdown`` and the call reports success.
"""

from __future__ import annotations

from crawler.notifiers.webhook import WebhookNotifier


def _fake_post(calls: list):
    def _post(url: str, payload: dict, headers: dict) -> str:
        calls.append((url, payload, headers))
        return "ok"
    return _post


def test_send_markdown_uses_markdown_template_and_returns_true():
    calls: list = []
    n = WebhookNotifier(
        kind="pushplus",
        token="PPTOKEN",
        _post=_fake_post(calls),
    )
    ok = n.send_markdown("政策日报 2026-08-12", "# 摘要\n- 要点")
    assert ok is True
    assert len(calls) == 1
    _url, payload, _headers = calls[0]
    assert payload["template"] == "markdown"
    assert payload["token"] == "PPTOKEN"
    assert "政策日报 2026-08-12" == payload["title"] or payload["title"].startswith("政策日报")


def test_send_markdown_clips_long_title_to_64_chars():
    calls: list = []
    n = WebhookNotifier(kind="pushplus", token="T", _post=_fake_post(calls))
    long_title = "政" * 100
    n.send_markdown(long_title, "body")
    _url, payload, _headers = calls[0]
    assert len(payload["title"]) <= 64


def test_send_markdown_returns_false_for_non_pushplus():
    n = WebhookNotifier(kind="generic", url="https://x/y", _post=_fake_post([]))
    assert n.send_markdown("t", "c") is False


def test_send_markdown_returns_false_on_transport_error():
    def _boom(url, payload, headers):
        raise RuntimeError("network down")
    n = WebhookNotifier(kind="pushplus", token="T", _post=_boom)
    assert n.send_markdown("t", "c") is False
