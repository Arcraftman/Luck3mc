"""Testing environment overrides.

Used by the test-suite: no network politeness constraints, no file logging
noise, and pipelines that are easy to assert on.
"""

from .base import *  # noqa: F401,F403

SCRAPY_ENV = "testing"

ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 0
AUTOTHROTTLE_ENABLED = False

LOG_LEVEL = "WARNING"
LOG_FILE = None  # type: ignore[assignment]  # keep test output clean

# Storage pipeline writes to a temp location during tests.
OUTPUT_DIR = "data/test_output"

# Don't dump raw HTML during the test-suite (keep it hermetic / fast).
SAVE_HTML = False

ITEM_PIPELINES = {
    "crawler.pipelines.validation.ValidationPipeline": 100,
    "crawler.pipelines.date_filter.DateFilterPipeline": 150,
    "crawler.pipelines.deduplication.DeduplicatePipeline": 200,
}
