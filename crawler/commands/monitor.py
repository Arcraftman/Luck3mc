"""``scrapy monitor`` — run one monitoring pass over all configured spiders.

Intended to be scheduled (e.g. every 6 hours via Windows Task Scheduler /
cron). Persistent de-duplication (when ``DATABASE_URL`` is set) ensures only
NEW urls are processed.

**Daily delivery model (changed 2026-08-13):** the *only* WeChat push in the
default flow is the consolidated DeepSeek ``.md`` report produced after the
crawl finishes (``crawler.services.report_generator``). The old per-item
NotifyPipeline is **OFF by default** — the operator wants one summary message,
not a stream of individual links. Re-enable per-item pushes with
``-s NOTIFY_ENABLED=1`` if ever needed.

Usage:
    SCRAPY_ENV=production scrapy monitor
"""

from __future__ import annotations

import datetime
import logging

from scrapy.commands import ScrapyCommand  # type: ignore

# Import CrawlerProcess inside run() to avoid importing Twisted/reactor at
# module import time (and to avoid static analysis issues in some editors).
from scrapy.utils.project import get_project_settings  # type: ignore

logger = logging.getLogger(__name__)


class Command(ScrapyCommand):
    requires_project = True
    default_settings = {"LOG_ENABLED": True}

    def syntax(self) -> str:
        return "[options]"

    def short_desc(self) -> str:
        return "Run one monitoring pass + push the consolidated .md report"

    def run(self, args, opts):
        settings = get_project_settings()

        # Import here to ensure the Twisted reactor isn't installed at
        # module-import time and to prevent some linters from flagging the
        # import when Scrapy isn't available in the analysis environment.
        from scrapy.crawler import CrawlerProcess  #type: ignore

        # The consolidated .md report is the single daily deliverable. Per-item
        # WeChat messages are OFF by default — re-enable with ``-s NOTIFY_ENABLED=1``.
        if "NOTIFY_ENABLED" not in settings:
            settings.set("NOTIFY_ENABLED", False)

        # Only surface items published *today* — never the historical backlog.
        # This keeps the daily pass clean on its very first run. Operators who
        # deliberately want the full history can opt out with
        # ``-s CRAWL_TODAY_ONLY=0``.
        if "CRAWL_TODAY_ONLY" not in settings:
            settings.set("CRAWL_TODAY_ONLY", True)

        spiders = list(settings.get("MONITOR_SPIDERS") or [])
        if not spiders:
            logger.error("MONITOR_SPIDERS is empty; nothing to monitor.")
            return

        if not settings.get("DATABASE_URL"):
            logger.warning(
                "No DATABASE_URL: de-dup is in-memory, so every monitor run "
                "will re-process items. Run `scrapy createdb`."
            )

        logger.info(
            "monitor: starting pass over %d spiders: %s", len(spiders), spiders
        )
        # CrawlerProcess installs the Twisted reactor from ``TWISTED_REACTOR``
        # (AsyncioSelectorReactor when Playwright is enabled) during its
        # __init__, i.e. AFTER settings are loaded. We must NOT import
        # ``twisted.internet.reactor`` at module level — doing so installs the
        # default SelectReactor first and breaks the asyncio requirement.
        runner = CrawlerProcess(settings)
        for name in spiders:
            runner.crawl(name)
        runner.start()

        # --- Post-crawl: generate + push the single consolidated .md report ---
        # This is the only WeChat delivery in the default flow. Safe to call
        # here: the Twisted reactor has already stopped, and the notifier uses
        # blocking ``urllib`` (no reactor interaction).
        self._push_daily_report()

    def _push_daily_report(self) -> None:
        """Generate the DeepSeek summary from today's jsonl and push it once."""
        try:
            from crawler.services import report_generator
        except Exception as exc:  # noqa: BLE001
            logger.error("monitor: cannot import report_generator: %s", exc)
            return
        try:
            result = report_generator.run(date_str=datetime.date.today().isoformat())
        except Exception as exc:  # noqa: BLE001
            # Crawl data is already persisted; a DeepSeek/push failure must not
            # crash the monitor. The report can be regenerated later.
            logger.error(
                "monitor: daily .md report failed (crawl data preserved): %s", exc
            )
            return
        if not result.get("items"):
            logger.info("monitor: no items crawled today; skipped .md push.")
            return
        logger.info(
            "monitor: pushed daily .md report (%d items) -> %s (pushed=%s)",
            result["items"], result.get("out"), result.get("pushed"),
        )
