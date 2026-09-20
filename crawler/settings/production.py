"""Production environment overrides.

Higher throughput, structured logging to a fixed file, and durable
storage pipelines. Secrets are pulled exclusively from the environment.
"""

from scrapy.settings import default_settings as _scrapy_defaults

from crawler.downloaders.playwright import (
    is_playwright_available,
    playwright_download_handlers,
)

from .base import *  # noqa: F401,F403

SCRAPY_ENV = "production"

# Scale up for server-side runs.
CONCURRENT_REQUESTS = 64
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 1.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0

LOG_LEVEL = "INFO"

# In production, persist to a database in addition to JSONL. The pipeline
# degrades to a no-op (with a warning) when DATABASE_URL is unset.
ITEM_PIPELINES = {
    "crawler.pipelines.validation.ValidationPipeline": 100,
    "crawler.pipelines.date_filter.DateFilterPipeline": 150,
    "crawler.pipelines.deduplication.DeduplicatePipeline": 200,
    "crawler.pipelines.notify.NotifyPipeline": 250,
    "crawler.pipelines.storage.JsonLinesExportPipeline": 300,
    "crawler.pipelines.storage.DatabasePipeline": 400,  # enabled; no-op if no DB
}

# ---------------------------------------------------------------------------
# Optional: Playwright handler for JavaScript-rendered lists (Layui / SPAs)
# ---------------------------------------------------------------------------
# Roots flagged ``js: true`` in gov_categories.yaml (e.g. 12366, zjtx) make
# PolicyRootBaseSpider attach ``meta["playwright"]`` to those domains' requests,
# which must be served by this handler. It is wired in ONLY when the optional
# ``scrapy-playwright`` extra is installed, so the rest of the project keeps
# working without a browser. One-time install:
#     pip install scrapy-playwright
#     playwright install chromium
if is_playwright_available():
    DOWNLOAD_HANDLERS = {
        **_scrapy_defaults.DOWNLOAD_HANDLERS,
        **playwright_download_handlers(),
    }
    # Playwright requires the asyncio reactor.
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
