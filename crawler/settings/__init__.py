"""Settings package entry point.

Scrapy imports this module as the project settings. The active
environment is resolved from the ``SCRAPY_ENV`` environment variable
(falls back to ``development``) and the matching module is star-imported
on top of :mod:`crawler.settings.base`.

Usage:
    scrapy crawl gov_policy_root          # 通用地方政策（gov_categories.yaml 的 local 块）
    scrapy crawl caishui                  # 财税政策（也是 MONITOR_SPIDERS 之一）
    SCRAPY_ENV=production scrapy crawl caishui
    SCRAPY_ENV=testing     scrapy crawl caishui
"""

import os

_ENV = os.environ.get("SCRAPY_ENV", "development").lower()

if _ENV == "production":
    from .production import *  # noqa: F401,F403
elif _ENV == "testing":
    from .testing import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
