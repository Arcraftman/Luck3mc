"""Keep only fiscal / tax *subsidy* policies.

The project monitors a broad set of government sites (tax, science & tech,
industry, SME, etc.). The operator's actual goal is **财税各种补贴政策** —
fiscal and tax subsidy policies — not the full firehose of every notice.

This pipeline is a content gate placed *before* de-duplication and storage: an
item survives only if its title / summary / body mentions a subsidy-related
keyword (补贴, 补助, 贴息, 留抵退税, 加计扣除, 以旧换新, 种粮补贴, …).
Everything else is dropped so downstream storage and WeChat notifications stay
focused on subsidy policies.

Keywords are configurable via ``SUBSIDY_KEYWORDS`` (settings) / ``monitor.
subsidy_keywords`` (YAML). The default list below is tuned for 财税补贴; trim
or extend it to taste.
"""

from __future__ import annotations

from itemadapter import ItemAdapter

from crawler.utils.keywords import (
    BODY_SAFE_KEYWORDS,
    DEFAULT_SUBSIDY_KEYWORDS,
    EXCLUSION_PHRASES,
)
from crawler.utils.log_config import get_logger


def _not_excluded(matched: list[str], text: str,
                  exclusions: tuple[str, ...]) -> bool:
    return any(
        kw for kw in matched
        if not any(ex in text and kw in ex for ex in exclusions)
    )


def matches_subsidy(
    title: str = "",
    summary: str = "",
    content: str = "",
    keywords=DEFAULT_SUBSIDY_KEYWORDS,
    exclusions: tuple[str, ...] = EXCLUSION_PHRASES,
    body_safe: tuple[str, ...] = BODY_SAFE_KEYWORDS,
) -> bool:
    """Return True if an item looks like a fiscal/tax subsidy policy.

    Precision-first rules:
      * Any keyword (even a weak one) in the **title/summary** is a strong
        signal — genuine subsidy policies name themselves there, while noisy
        news articles rarely mention a specific instrument in the headline.
      * A *program* keyword from ``body_safe`` may also fire from the **body**,
        catching notices with a generic title but explicit subsidy language.
        Generic terms (bare 补贴/退税/免税/税收优惠) are intentionally absent
        from ``body_safe`` so they can't trigger on passing news mentions.
      * Trade-remedy false positives (反补贴 / 反倾销) are excluded.

    Used by both :class:`SubsidyFilterPipeline` and the weekly digest, which
    re-screens historical JSONL so pre-filter rows don't leak into the summary.
    """
    head = f"{title or ''}\n{summary or ''}"
    full = f"{head}\n{content or ''}"
    if not full.strip():
        return False

    # 1) Any keyword in title/summary.
    head_match = [kw for kw in keywords if kw in head]
    if _not_excluded(head_match, head, exclusions):
        return True

    # 2) Program keyword anywhere in the document body.
    body_match = [kw for kw in body_safe if kw in full]
    return bool(_not_excluded(body_match, full, exclusions))


class SubsidyFilterPipeline:
    """Drop items that are not about fiscal/tax subsidy policies."""

    def __init__(self, keywords):
        self.keywords = tuple(keywords) if keywords else DEFAULT_SUBSIDY_KEYWORDS
        self.kept = 0
        self.dropped = 0
        self.logger = get_logger(__name__)

    @classmethod
    def from_crawler(cls, crawler):
        keywords = crawler.settings.get("SUBSIDY_KEYWORDS") or []
        return cls(keywords)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        title = adapter.get("title") or ""
        summary = adapter.get("summary") or ""
        content = adapter.get("content") or ""
        if not (title or summary or content):
            # No inspectable text — can't assert it's a subsidy; keep it so we
            # don't silently lose items that simply lack a parsed field yet.
            self.kept += 1
            return item
        if not matches_subsidy(
            title=title, summary=summary, content=content,
            keywords=self.keywords, exclusions=EXCLUSION_PHRASES,
        ):
            self.dropped += 1
            self.logger.debug(
                "SubsidyFilter dropped (not a subsidy policy): %s",
                adapter.get("source_url") or adapter.get("title"),
            )
            return None
        self.kept += 1
        return item

    def close_spider(self, spider):
        if self.dropped:
            self.logger.info(
                "SubsidyFilterPipeline kept %d, dropped %d non-subsidy items.",
                self.kept, self.dropped,
            )
