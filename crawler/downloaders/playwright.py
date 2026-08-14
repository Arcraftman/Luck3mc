"""Optional Playwright download handler for JavaScript-rendered sites.

Several target sites render their lists with JavaScript (Layui tables, SPAs)
and therefore return an empty shell to plain Scrapy:

* ``fgk.chinatax.gov.cn`` (core tax policy library) — Layui list
* ``fgk.mof.gov.cn`` — SPA hash route
* ``12366.chinatax.gov.cn`` — JS-heavy Q&A platform
* ``zjtx.miit.gov.cn`` — login-gated SME platform

For these, the config-driven spider ``PolicyRootBaseSpider`` injects
``meta["playwright"] = True`` on requests whose root is flagged ``js: true`` in
``gov_categories.yaml`` (no per-site code). Those requests must be served by the
Playwright download handler. This module wires that handler in *only when* the
``scrapy-playwright`` extra is installed, so the rest of the project keeps
working without a browser.

Installation (one time):
    pip install scrapy-playwright
    playwright install chromium        # downloads the browser binary

Enable in a settings module (e.g. production.py) *after* the extra is present:
    from crawler.downloaders.playwright import playwright_download_handlers
    DOWNLOAD_HANDLERS = {
        **DOWNLOAD_HANDLERS,
        **playwright_download_handlers(),
    }

Spiders opt in per-request via ``meta["playwright"]``; non-Playwright spiders
are unaffected.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util

# Detect the optional extra WITHOUT importing its handler module. Importing
# ``scrapy_playwright.handler`` at module load time executes
# ``from twisted.internet import reactor`` while no reactor is installed yet,
# which installs Twisted's default SelectReactor *before* Scrapy can apply
# ``TWISTED_REACTOR = AsyncioSelectorReactor`` — raising
# "installed reactor does not match requested". Using ``find_spec`` avoids that
# premature import; the handler is only loaded lazily (by string) when a
# Playwright request is actually dispatched, by which point Scrapy has already
# installed the asyncio reactor.
_HAS_PLAYWRIGHT = importlib.util.find_spec("scrapy_playwright") is not None


def _resolve_pw_handler() -> str:
    """Pick the correct Playwright download-handler class path for the
    installed ``scrapy-playwright`` version.

    The handler class was renamed from ``PlaywrightDownloadHandler`` to
    ``ScrapyPlaywrightDownloadHandler`` in 0.0.47. We resolve it by version
    through ``importlib.metadata`` — which reads distribution metadata only and
    does NOT import the handler module. Importing ``scrapy_playwright.handler``
    at settings-import time would otherwise pull in Twisted and install the
    wrong reactor before Scrapy can apply
    ``TWISTED_REACTOR = AsyncioSelectorReactor``.
    """
    try:
        ver = importlib.metadata.version("scrapy-playwright")
        parts = tuple(int(x) for x in ver.split(".") if x.isdigit())
    except Exception:
        parts = (0, 0, 0)
    if parts >= (0, 0, 47):
        return "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler"
    return "scrapy_playwright.handler.PlaywrightDownloadHandler"


def playwright_download_handlers() -> dict[str, str]:
    """Return the ``DOWNLOAD_HANDLERS`` entries for Playwright.

    Raises a clear error if the ``scrapy-playwright`` package is missing so the
    failure is obvious rather than a silent no-op.
    """
    if not _HAS_PLAYWRIGHT:
        raise RuntimeError(
            "scrapy-playwright is not installed. Run:\n"
            "  pip install scrapy-playwright\n"
            "  playwright install chromium\n"
            "Then enable DOWNLOAD_HANDLERS in your settings module."
        )
    handler = _resolve_pw_handler()
    return {
        "https": handler,
        "http": handler,
    }


def is_playwright_available() -> bool:
    return _HAS_PLAYWRIGHT
