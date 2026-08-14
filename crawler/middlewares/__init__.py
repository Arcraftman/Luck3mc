"""Downloader / spider middlewares.

Keep middlewares lightweight and generic: user-agent rotation, polite proxy
attachment, and retry handling. Site-specific parsing logic belongs in spiders.
"""

from .proxy import ProxyMiddleware
from .retry import PoliteRetryMiddleware
from .user_agent import RandomUserAgentMiddleware

__all__ = [
    "RandomUserAgentMiddleware",
    "ProxyMiddleware",
    "PoliteRetryMiddleware",
]
