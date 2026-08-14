"""Attach a rotating proxy to outgoing requests (disabled if no pool)."""

from scrapy import signals

from crawler.utils.proxy_rotator import build_rotator


class ProxyMiddleware:
    """Sets ``meta['proxy']`` per request from a configured proxy pool."""

    @classmethod
    def from_crawler(cls, crawler):
        rotator = build_rotator()
        middleware = cls(rotator)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def __init__(self, rotator) -> None:
        self.rotator = rotator

    def process_request(self, request, spider):
        if not self.rotator.enabled:
            return
        # Allow a spider/request to opt out or pin a specific proxy.
        if request.meta.get("no_proxy"):
            return
        proxy = request.meta.get("proxy") or self.rotator.next()
        if proxy:
            request.meta["proxy"] = proxy

    def spider_opened(self, spider):
        if self.rotator.enabled:
            spider.logger.info("ProxyMiddleware enabled (rotating pool).")
        else:
            spider.logger.info("ProxyMiddleware disabled (no proxy pool configured).")
