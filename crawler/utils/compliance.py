"""Compliance / politeness shared helpers.

Centralises the WAF / anti-bot block-page detection so every config-driven
spider suspends only the affected host when an access-control page is found.
Public pages with incidental login forms are not access-control pages.
"""

from __future__ import annotations

from parsel import Selector

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


def is_compliance_blocked(text: str | None, status: int = 200) -> bool:
    """Detect access-control pages, not incidental login widgets/scripts."""
    if status in (401, 403, 429):
        return True
    if not text:
        return False
    selector = Selector(text=text)
    title = " ".join(selector.css("title::text, h1::text").getall()).lower()
    markers = [marker.lower() for marker in WAF_MARKERS]
    if any(marker in title for marker in markers):
        return True
    if any(word in title for word in ("用户登录", "统一身份认证", "用户认证", "sign in")):
        if selector.css('input[type="password"]'):
            return True
    visible = " ".join(selector.xpath(
        "//text()[not(ancestor::script) and not(ancestor::style) "
        "and not(ancestor::form)]"
    ).getall()).strip().lower()
    strong = ("请求已被阻断", "您的请求已被", "access denied", "403 forbidden")
    if len(visible) < 1500 and any(marker in visible for marker in strong):
        return True
    # A short verification page with no public article/list content is a wall.
    challenge = any(marker in visible for marker in ("人机验证", "安全验证", "请输入验证码"))
    public_links = selector.xpath("//a[@href and normalize-space(string(.)) != '']")
    return len(visible) < 500 and challenge and len(public_links) < 3
