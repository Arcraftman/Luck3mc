"""Check retry waiting lets other reactor work execute, using a real reactor."""
import subprocess
import sys


def test_retry_delay_is_nonblocking_and_nonretry_errors_are_ignored():
    code = '''
import asyncio
from scrapy.utils.reactor import install_reactor
install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")
from scrapy import Request
from scrapy.http import Response
from scrapy.settings import Settings
from scrapy.exceptions import IgnoreRequest
from crawler.middlewares.retry import PoliteRetryMiddleware
async def check():
    middleware = PoliteRetryMiddleware(Settings())
    request = Request("https://example.org", meta={"_polite_retry_delay": 0.1})
    middleware._retry = lambda request, reason: request.copy()
    pending = asyncio.create_task(middleware.process_response(
        request, Response(request.url, status=503), None))
    await asyncio.sleep(0.01)
    assert not pending.done(), "retry blocked the event loop"
    assert isinstance(await pending, Request)
    assert await middleware.process_exception(request, IgnoreRequest(), None) is None
asyncio.get_event_loop().run_until_complete(check())
'''
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True,
                   text=True, timeout=15)
