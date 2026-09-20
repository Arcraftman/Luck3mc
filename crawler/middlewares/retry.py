"""Polite retry middleware with jittered backoff.

Replaces Scrapy's default ``RetryMiddleware`` so we can add a small random
delay between retries and avoid hammering a site that is rate-limiting us.
"""

import random

from scrapy.utils.defer import maybe_deferred_to_future
from twisted.internet.task import deferLater

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message


class PoliteRetryMiddleware(RetryMiddleware):
    """Retry with randomised backoff; respects ``meta['_polite_retry_delay']``."""

    async def _wait(self, request):
        # Import lazily so Scrapy can install its configured reactor first.
        from twisted.internet import reactor
        delay = request.meta.get("_polite_retry_delay")
        if delay is None:
            delay = random.uniform(1.0, 4.0)
        await maybe_deferred_to_future(deferLater(reactor, delay, lambda: None))

    async def process_response(self, request, response, spider):
        if request.meta.get("dont_retry", False):
            return response
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            retry = self._retry(request, reason)
            if retry:
                await self._wait(request)
            return retry or response
        return response

    async def process_exception(self, request, exception, spider):
        if request.meta.get("dont_retry", False):
            return None
        if not isinstance(exception, self.exceptions_to_retry):
            return None
        retry = self._retry(request, exception)
        if retry:
            await self._wait(request)
        return retry
