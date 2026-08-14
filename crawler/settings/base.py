"""Base settings shared by every environment.

Environment-specific modules (development / production / testing) import
everything from here with ``from .base import *`` and then override only
the values that differ. Keep environment-agnostic and non-secret config here.
"""

import os
from pathlib import Path

from ..utils.config_loader import apply_config, load_config

# ---------------------------------------------------------------------------
# Project identity
# ---------------------------------------------------------------------------
BOT_NAME = "crawler"

# Spider discovery. Scrapy walks this package recursively, so sub-packages
# such as ``crawler.spiders.chinatax`` are discovered automatically — do NOT
# also list them here (that double-registers spiders and triggers a warning).
SPIDER_MODULES = [
    "crawler.spiders",
]
NEWSPIDER_MODULE = "crawler.spiders"

# Custom Scrapy commands live here (e.g. `createdb`).
COMMANDS_MODULE = "crawler.commands"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Compliance & politeness (override per-env)
# ---------------------------------------------------------------------------
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = 0.5
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# ---------------------------------------------------------------------------
# Retry / timeout
# ---------------------------------------------------------------------------
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_MAXSIZE = 8 * 1024 * 1024  # 8 MiB
DOWNLOAD_WARNSIZE = 4 * 1024 * 1024

# ---------------------------------------------------------------------------
# HTTP / network
# ---------------------------------------------------------------------------
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False

# Bypass the system proxy entirely. Scrapy's built-in HttpProxyMiddleware reads
# the ``http_proxy`` / ``https_proxy`` env vars; when those point at a dead or
# unwanted proxy (e.g. 127.0.0.1:7897 injected by the host), every request fails.
# We disable it and drive proxies exclusively through our own rotating pool
# (``crawler.middlewares.proxy.ProxyMiddleware`` via PROXY_POOL / PROXY_API_URL).
# Set this to True only if you deliberately want Scrapy to honor a system proxy.
HTTPPROXY_ENABLED = False

# ---------------------------------------------------------------------------
# Item pipelines (order = priority, lower runs first)
# ---------------------------------------------------------------------------
ITEM_PIPELINES = {
    "crawler.pipelines.validation.ValidationPipeline": 100,
    # 补贴关键词过滤已按需求关闭（全局不再用特定词筛掉条目）。
    # "crawler.pipelines.subsidy_filter.SubsidyFilterPipeline": 120,
    "crawler.pipelines.date_filter.DateFilterPipeline": 150,
    "crawler.pipelines.deduplication.DeduplicatePipeline": 200,
    "crawler.pipelines.backend_sink.BackendSinkPipeline": 245,
    "crawler.pipelines.notify.NotifyPipeline": 250,
    "crawler.pipelines.storage.JsonLinesExportPipeline": 300,
}

# ---------------------------------------------------------------------------
# Downloader / spider middlewares
# ---------------------------------------------------------------------------
DOWNLOADER_MIDDLEWARES = {
    "crawler.middlewares.user_agent.RandomUserAgentMiddleware": 400,
    "crawler.middlewares.proxy.ProxyMiddleware": 500,
    "crawler.middlewares.retry.PoliteRetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,  # replaced
}

SPIDER_MIDDLEWARES: dict = {}

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
EXTENSIONS = {
    "crawler.extensions.StatsLoggingExtension": 500,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = str(LOGS_DIR / f"{BOT_NAME}.log")

# ---------------------------------------------------------------------------
# Feed / export defaults (used when a spider yields without a pipeline sink)
# ---------------------------------------------------------------------------
FEED_EXPORT_ENCODING = "utf-8"

# ---------------------------------------------------------------------------
# Custom project config (read from environment so secrets never hit VCS)
# ---------------------------------------------------------------------------
# Proxy pool: comma-separated list of "scheme://host:port" or a URL to a
# proxy API. Leave empty to disable proxy rotation. (Overridden by config YAML.)
PROXY_POOL = os.environ.get("PROXY_POOL", "")
PROXY_API_URL = os.environ.get("PROXY_API_URL", "")

# Database / storage connection strings (never commit real values).
DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")

# Default output location for crawled items.
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", str(DATA_DIR))

# Save the raw HTML of every crawled page to disk. OFF by default — the
# monitoring use case only needs URLs, not archived HTML. Files would land at
# ``<OUTPUT_DIR>/html/<spider>/<list|detail>/<url>.html``.
SAVE_HTML = False

# ---------------------------------------------------------------------------
# Notification (monitor -> WeChat)
# ---------------------------------------------------------------------------
# When a *new* URL is discovered during a ``scrapy monitor`` run, post it to a
# chat. Personal WeChat has no official API, so the recommended backend is
# ``webhook`` with Server酱 / pushplus (delivers to your personal WeChat as a
# service message). For a real group bot, use ``wechaty`` (see notifiers/wechaty.py).
NOTIFY_ENABLED = os.environ.get("NOTIFY_ENABLED", "false").lower() in ("1", "true", "yes")
NOTIFY_BACKEND = os.environ.get("NOTIFY_BACKEND", "webhook")  # webhook | wechaty
NOTIFY_WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL", "")
NOTIFY_WEBHOOK_KIND = os.environ.get("NOTIFY_WEBHOOK_KIND", "generic")  # serverchan|pushplus|wecom|generic
NOTIFY_WEBHOOK_TOKEN = os.environ.get("NOTIFY_WEBHOOK_TOKEN", "")
NOTIFY_TARGET = os.environ.get("NOTIFY_TARGET", "")  # wechaty: room/topic name

# ---------------------------------------------------------------------------
# Monitor (scheduled 24h polling)
# ---------------------------------------------------------------------------
# Spiders swept on each ``scrapy monitor`` pass. Order does not matter. Every
# entry maps to a category block (or gov_general) in gov_categories.yaml. The
# JS-rendered roots (12366, zjtx) are flagged ``js: true`` there, so the spider
# requests them via scrapy-playwright automatically — no per-spider hard-coding.
# ``gongxin`` is deliberately omitted: it is an empty placeholder category with
# no roots, so the spider would CloseSpider immediately.
MONITOR_SPIDERS = [
    "gov_policy_root",
    "caishui",
    "gaoqi",
    "yanfa",
    "kexiao",
]

# ---------------------------------------------------------------------------
# Subsidy-policy gate (only retain 财税补贴政策 items)
# ---------------------------------------------------------------------------
# ``SubsidyFilterPipeline`` keeps an item only if its title/summary/body mentions
# a subsidy keyword. Default list lives in the pipeline module; override here or
# via ``monitor.subsidy_keywords`` in config YAML.
from crawler.utils.keywords import DEFAULT_SUBSIDY_KEYWORDS  # noqa: E402

SUBSIDY_KEYWORDS = list(DEFAULT_SUBSIDY_KEYWORDS)

# ---------------------------------------------------------------------------
# Externalised YAML configuration
# ---------------------------------------------------------------------------
# ``config/<SCRAPY_ENV>.yaml`` is the operator-tunable source of truth for
# politeness / proxy / storage / logging. It overlays the defaults above;
# environment-specific modules may still override individual values after.
apply_config(globals())
CONFIG = load_config()
