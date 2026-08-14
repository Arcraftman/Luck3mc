"""Pluggable notification backends.

The crawler notifies operators when a *new* policy URL is discovered during a
monitor run. Backends:

* ``webhook`` — POST to any HTTP webhook (Server酱 / pushplus / 企业微信机器人 /
               generic). This is the recommended path for personal-WeChat push:
               Server酱 and pushplus deliver straight to your personal WeChat as
               a service notification — no official bot API needed.
* ``wechaty`` — drive a real personal WeChat account as a bot to post into a
               group. Requires ``wechaty`` + a puppet service and carries
               ban / compliance risk. Scaffold only; NOT enabled by default.

Select via ``NOTIFY_BACKEND`` (config ``notify.backend``).
"""

from .base import Notifier, NotifyMessage
from .webhook import WebhookNotifier
from .wechaty import WechatyNotifier

__all__ = [
    "Notifier",
    "NotifyMessage",
    "WebhookNotifier",
    "WechatyNotifier",
    "get_notifier",
]


def get_notifier(settings) -> "Notifier | None":
    """Build the configured notifier from Scrapy ``settings``."""
    backend = (settings.get("NOTIFY_BACKEND") or "webhook").lower()
    if backend == "webhook":
        return WebhookNotifier(
            url=settings.get("NOTIFY_WEBHOOK_URL") or "",
            kind=settings.get("NOTIFY_WEBHOOK_KIND") or "generic",
            token=settings.get("NOTIFY_WEBHOOK_TOKEN") or "",
        )
    if backend == "wechaty":
        return WechatyNotifier(
            token=settings.get("NOTIFY_WEBHOOK_TOKEN") or "",
            room=settings.get("NOTIFY_TARGET") or "",
        )
    raise ValueError(f"Unknown NOTIFY_BACKEND: {backend!r}")
