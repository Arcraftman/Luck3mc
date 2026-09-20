"""Stop requests to a blocked host without stopping unrelated sources."""
from urllib.parse import urlparse

from scrapy.exceptions import IgnoreRequest
from scrapy.http import TextResponse

from crawler.utils.compliance import is_compliance_blocked


class SiteGuardMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        return instance

    def process_request(self, request, spider):
        blocked = getattr(spider, "blocked_domains", set())
        if urlparse(request.url).hostname in blocked:
            request.meta["dont_retry"] = True
            raise IgnoreRequest("site_guard: host suspended for this run")

    def process_response(self, request, response, spider):
        if not hasattr(spider, "block_site"):
            return response
        if urlparse(request.url).hostname in spider.blocked_domains:
            request.meta["dont_retry"] = True
            raise IgnoreRequest("site_guard: host suspended for this run")
        # robots.txt 403/429 is handled by the robots middleware, not a signal
        # that a public article itself is inaccessible.
        if urlparse(request.url).path == "/robots.txt":
            return response
        body = response.text if isinstance(response, TextResponse) else ""
        if is_compliance_blocked(body, response.status):
            source = request.meta.get("redirect_urls", [request.url])[0]
            spider.block_site(source, response.url)
            request.meta["dont_retry"] = True
            raise IgnoreRequest("site_guard: access-control response")
        return response
