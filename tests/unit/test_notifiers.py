"""Unit tests for the pluggable notification backends."""

from __future__ import annotations

from crawler.notifiers import (
    NotifyMessage,
    WebhookNotifier,
    WechatyNotifier,
    get_notifier,
)
from crawler.notifiers.webhook import WebhookNotifier as WH


def _fake_post(calls):
    def _post(url, payload, headers):
        calls.append((url, payload, headers))
        return "ok"
    return _post


def test_render_text_includes_fields():
    m = NotifyMessage(
        title="研发费用加计扣除新政",
        url="https://fgk.chinatax.gov.cn/abc.html",
        pub_date="2026-02-23",
        source_site="chinatax.gov.cn",
    )
    text = m.render_text()
    assert "研发费用加计扣除新政" in text
    assert "https://fgk.chinatax.gov.cn/abc.html" in text
    assert "2026-02-23" in text
    assert "chinatax.gov.cn" in text


def test_webhook_generic_posts_to_url():
    calls: list = []
    n = WH(url="https://example.com/hook", kind="generic", _post=_fake_post(calls))
    ok = n.send(NotifyMessage(title="T", url="https://x/y", pub_date="2026-01-01", source_site="s"))
    assert ok is True
    assert len(calls) == 1
    url, payload, headers = calls[0]
    assert url == "https://example.com/hook"
    assert payload["url"] == "https://x/y"
    assert payload["title"] == "T"
    assert headers["Content-Type"].startswith("application/json")


def test_webhook_serverchan_endpoint_and_payload():
    calls: list = []
    n = WH(kind="serverchan", token="SECRET", _post=_fake_post(calls))
    n.send(NotifyMessage(title="标题", url="https://x/y"))
    url, payload, _ = calls[0]
    assert url == "https://sctapi.ftqq.com/SECRET.send"
    assert payload["title"] == "标题"
    assert "链接" in payload["desp"]


def test_webhook_pushplus_endpoint_and_payload():
    calls: list = []
    n = WH(kind="pushplus", token="PPTOKEN", _post=_fake_post(calls))
    n.send(NotifyMessage(title="T", url="https://x/y"))
    url, payload, _ = calls[0]
    assert url == "https://www.pushplus.plus/send"
    assert payload["token"] == "PPTOKEN"
    assert payload["template"] == "txt"


def test_webhook_wecom_payload():
    calls: list = []
    n = WH(kind="wecom", url="https://qyapi.weixin.qq.com/x", _post=_fake_post(calls))
    n.send(NotifyMessage(title="T", url="https://x/y"))
    _, payload, _ = calls[0]
    assert payload["msgtype"] == "text"
    assert "https://x/y" in payload["text"]["content"]


def test_webhook_send_returns_false_on_error():
    def _boom(url, payload, headers):
        raise RuntimeError("network down")
    n = WH(url="https://example.com/hook", kind="generic", _post=_boom)
    assert n.send(NotifyMessage(title="T", url="https://x/y")) is False


def test_webhook_send_returns_false_without_url():
    n = WH(url="https://example.com/hook", kind="generic", _post=_fake_post([]))
    assert n.send(NotifyMessage(title="T", url="")) is False


def test_get_notifier_webhook():
    cfg = {"NOTIFY_BACKEND": "webhook", "NOTIFY_WEBHOOK_URL": "u", "NOTIFY_WEBHOOK_KIND": "generic", "NOTIFY_WEBHOOK_TOKEN": ""}
    assert isinstance(get_notifier(cfg), WebhookNotifier)


def test_get_notifier_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        get_notifier({"NOTIFY_BACKEND": "nope"})


def test_wechaty_scaffold_never_raises_and_returns_false():
    n = WechatyNotifier(token="", room="我的群")
    # Without the `wechaty` package installed this degrades to a no-op.
    assert n.send(NotifyMessage(title="T", url="https://x/y")) is False
