"""Ergonomic ItemLoader construction.

Newer ``itemloaders`` (>=1.1) no longer derives a selector from a ``response``
argument, so always build the loader from an explicit ``Selector``. This helper
keeps spider code short and consistent.

Usage::

    from crawler.utils.loaders import build_loader
    loader = build_loader(TaxPolicyItem(), response)
    loader.add_css("title", "div.article_title::text")
"""

from itemloaders import ItemLoader
from scrapy.selector import Selector


def build_loader(item, response) -> ItemLoader:
    """Return an ``ItemLoader`` bound to ``response`` via a fresh Selector."""
    return ItemLoader(item=item, selector=Selector(response))
