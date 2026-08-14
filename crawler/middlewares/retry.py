"""Polite retry middleware with jittered backoff.

Replaces Scrapy's default ``RetryMiddleware`` so we can add a small random
delay between retries and avoid hammering a site that is rate-limiting us.
"""

import random
import time

from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message


class PoliteRetryMiddleware(RetryMiddleware):
    """Retry with randomised backoff; respects ``meta['_polite_retry_delay']``."""

    def _wait(self, request):
        delay = request.meta.get("_polite_retry_delay")
        if delay is None:
            delay = random.uniform(1.0, 4.0)
        time.sleep(delay)

    def process_response(self, request, response, spider):
        if request.meta.get("dont_retry", False):
            return response
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            self._wait(request)
            return self._retry(request, reason) or response
        return response

    def process_exception(self, request, exception, spider):
        if request.meta.get("dont_retry", False):
            return None
        self._wait(request)
        return self._retry(request, str(exception))
