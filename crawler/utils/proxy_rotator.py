"""Proxy rotation utility.

Reads a static pool (comma-separated env var) or fetches from a proxy API.
``ProxyMiddleware`` consumes this to attach a rotating proxy per request.
"""

import os
import random
import urllib.request


class ProxyRotator:
    """Round-robins a static proxy pool, optionally backed by an API."""

    def __init__(
        self,
        pool: str | None = None,
        api_url: str | None = None,
    ) -> None:
        self._static = [p.strip() for p in (pool or "").split(",") if p.strip()]
        self._api_url = api_url or ""
        self._index = 0

    @property
    def enabled(self) -> bool:
        return bool(self._static) or bool(self._api_url)

    def _fetch_from_api(self) -> str | None:
        if not self._api_url:
            return None
        try:
            with urllib.request.urlopen(self._api_url, timeout=5) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception:
            return None

    def next(self) -> str | None:
        """Return the next proxy URL, or ``None`` if rotation is disabled."""
        if self._static:
            proxy = self._static[self._index % len(self._static)]
            self._index += 1
            return proxy
        if self._api_url:
            return self._fetch_from_api()
        return None

    def random(self) -> str | None:
        if self._static:
            return random.choice(self._static)
        return self._fetch_from_api()


def build_rotator() -> ProxyRotator:
    """Construct a rotator from the project's environment configuration."""
    return ProxyRotator(
        pool=os.environ.get("PROXY_POOL", ""),
        api_url=os.environ.get("PROXY_API_URL", ""),
    )
