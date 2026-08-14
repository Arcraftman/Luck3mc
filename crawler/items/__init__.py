"""Item definitions for State Taxation Administration crawling.

Each business domain has its own module under ``crawler/items`` so that
item schemas stay small and decoupled. Re-export the commonly used items here
for convenient imports: ``from crawler.items import TaxPolicyItem``.
"""

from .tax_items import (
    TaxAnnouncementItem,
    TaxNewsItem,
    TaxPolicyItem,
    TaxServiceGuideItem,
)

__all__ = [
    "TaxPolicyItem",
    "TaxAnnouncementItem",
    "TaxNewsItem",
    "TaxServiceGuideItem",
]
