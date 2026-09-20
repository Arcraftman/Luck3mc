"""Development environment overrides.

Conservative, verbose, polite — safe for local iteration.
"""

from scrapy.settings import default_settings as _scrapy_defaults

from crawler.downloaders.playwright import (
    is_playwright_available,
    playwright_download_handlers,
)

from .base import *  # noqa: F401,F403

SCRAPY_ENV = "development"

# Be gentle while developing.
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2.0
AUTOTHROTTLE_DEBUG = True

LOG_LEVEL = "DEBUG"

# Local filesystem output is fine for dev.
ITEM_PIPELINES = {
    "crawler.pipelines.validation.ValidationPipeline": 100,
    "crawler.pipelines.date_filter.DateFilterPipeline": 150,
    "crawler.pipelines.deduplication.DeduplicatePipeline": 200,
    "crawler.pipelines.notify.NotifyPipeline": 250,
    "crawler.pipelines.storage.JsonLinesExportPipeline": 300,
}

# ---------------------------------------------------------------------------
# Optional: Playwright handler for JavaScript-rendered lists (Layui / SPAs)
# ---------------------------------------------------------------------------
# Wired in ONLY when the optional ``scrapy-playwright`` extra is installed.
# See production.py for the install commands. Spiders opt in per-request via
# ``meta["playwright"]``; non-Playwright spiders are unaffected.
if is_playwright_available():
    DOWNLOAD_HANDLERS = {
        **_scrapy_defaults.DOWNLOAD_HANDLERS,
        **playwright_download_handlers(),
    }
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
