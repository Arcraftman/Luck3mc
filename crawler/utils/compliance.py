"""Compliance / politeness shared helpers.

Centralises the WAF / anti-bot block-page detection so every config-driven
spider (built on ``PolicyRootBaseSpider``) refuses to keep crawling the moment
it hits an access-control page. We deliberately *stop* rather than retry or
evade — respecting the site's controls is the compliant behaviour.
"""

from __future__ import annotations

# Substrings that indicate an anti-bot / WAF / human-verification block page.
# When one is found we stop the crawl politely. Extend here as new markers
# appear; subclasses may add their own (e.g. login walls) without touching
# the spiders.
WAF_MARKERS: list[str] = [
    "请求已被阻断",
    "访问受限",
    "安全验证",
    "您的请求已被",
    "Access Denied",
    "403 Forbidden",
    "人机验证",
    "验证码",
]


def is_compliance_blocked(text: str | None) -> bool:
    """Return True if ``text`` looks like an anti-bot / WAF block page."""
    if not text:
        return False
    return any(marker in text for marker in WAF_MARKERS)
