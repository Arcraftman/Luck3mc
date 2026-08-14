"""Reusable data-cleaning processors for ItemLoaders and pipelines.

These are stateless callables so they can be used both as
``MapCompose`` processors in item field definitions and directly inside
spider parse methods.
"""

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

_WS_RE = re.compile(r"\s+")


def clean_text(value):
    """Strip, collapse internal whitespace, and drop empty strings."""
    if value is None:
        return None
    text = str(value).strip()
    text = _WS_RE.sub(" ", text)
    return text or None


def parse_pub_date(value):
    """Best-effort parse of Chinese/English date strings into ISO ``YYYY-MM-DD``.

    Accepts formats like ``2026-08-11``, ``2026年08月11日``,
    ``2026/8/11 10:30``, ``August 11, 2026``.
    """
    if not value:
        return None
    text = clean_text(value)
    if not text:
        return None

    # Normalise Chinese separators.
    text = text.replace("年", "-").replace("月", "-").replace("日", "")
    text = text.replace("/", "-")

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: pull the first YYYY-MM-DD-like token.
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3))
            ).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def normalize_url(value, base=None):
    """Join relative URLs against ``base`` and strip fragments/query noise."""
    if not value:
        return None
    url = str(value).strip()
    if base:
        url = urljoin(base, url)
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url.lstrip("/")
    # Drop fragment; keep query for detail pages that rely on it.
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (
        f"?{parsed.query}" if parsed.query else ""
    )


def to_int_or_none(value):
    """Extract the first integer from a messy string, else ``None``."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"-?\d+", str(value))
    return int(m.group(0)) if m else None
