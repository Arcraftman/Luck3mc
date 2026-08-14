"""Fiscal/tax subsidy keyword constants.

Extracted from :mod:`crawler.pipelines.subsidy_filter` so that settings and
the notify pipeline no longer depend on the ``pipelines`` layer just to read
the default keyword list. This keeps ``subsidy_filter`` (which may be disabled
in ``ITEM_PIPELINES``) decoupled from the rest of the project.
"""

from __future__ import annotations

# Default fiscal/tax subsidy keyword list. Curated to favour genuine subsidy
# instruments over generic policy prose (so we don't drown in noise).
DEFAULT_SUBSIDY_KEYWORDS: tuple[str, ...] = (
    # 直接补贴 / 补助
    "补贴", "补助", "贴息", "奖补", "财政补贴", "资金补贴", "专项补贴",
    "补助资金", "补贴资金", "财政奖补", "补助经费", "财政补助",
    # 税收减免 / 退税（税侧补贴）
    "退税", "留抵退税", "出口退税", "税收优惠", "税费优惠", "减税降费",
    "加计扣除", "税前抵扣", "税收返还", "即征即退", "先征后返", "免征",
    "免税", "缓税", "税收减免",
    # 稳岗 / 就业 / 社保
    "稳岗", "扩岗", "就业补贴", "社保补贴", "见习补贴", "创业补贴",
    # 重点补贴项目
    "农机购置补贴", "购置补贴", "新能源汽车补贴", "充电补贴", "以旧换新",
    "消费补贴", "价格补贴", "种粮补贴", "农资补贴", "燃油补贴",
    "耕地地力保护补贴", "危房改造补助", "保障性住房", "困难群众救助", "低保",
    # 创新 / 纾困 / 专项资金
    "研发补贴", "创新券", "纾困", "专项资金", "扶持资金", "奖励资金",
    "财政扶持", "财政专项资金",
)

# Trade-remedy phrases that contain "补贴" but are NOT fiscal/tax subsidies
# (e.g. 反补贴税 / 反倾销反补贴调查). When the only subsidy-looking match in a
# document is one of these, the item is dropped as off-topic.
EXCLUSION_PHRASES: tuple[str, ...] = (
    "反补贴",
    "反倾销",
    "补贴贸易",
    "补贴协定",
    "补贴与反补贴",
)

# Subsidy *program* keywords safe to trust when they appear only in the body.
# These name concrete instruments (e.g. 以旧换新, 种粮补贴, 留抵退税) that
# almost never appear incidentally in general news, so a body-only hit is
# reliable. Generic terms like bare 补贴/退税/免税/税收优惠 are deliberately
# EXCLUDED here — they show up in passing in tax-news articles and would cause
# false positives, so they are only trusted in the title/summary (see the
# DEFAULT_SUBSIDY_KEYWORDS head-match rule below).
BODY_SAFE_KEYWORDS: tuple[str, ...] = (
    "以旧换新", "购置补贴", "新能源汽车补贴", "农机购置补贴", "种粮补贴",
    "农资补贴", "燃油补贴", "耕地地力保护补贴", "危房改造补助", "保障性住房",
    "困难群众救助", "低保", "稳岗", "扩岗", "就业补贴", "社保补贴",
    "见习补贴", "创业补贴", "研发补贴", "创新券", "贴息", "奖补",
    "财政补贴", "资金补贴", "专项补贴", "补助资金", "补贴资金", "财政奖补",
    "补助经费", "财政补助", "税前抵扣", "税收返还", "即征即退", "先征后返",
    "留抵退税", "出口退税", "加计扣除",
)

# Backwards-compatible alias: an earlier design named this constant
# ``HIGH_SPECIFICITY_KEYWORDS``; it is the same set now exported as
# ``BODY_SAFE_KEYWORDS``. Kept so any external reference keeps working.
HIGH_SPECIFICITY_KEYWORDS = BODY_SAFE_KEYWORDS

__all__ = [
    "DEFAULT_SUBSIDY_KEYWORDS",
    "EXCLUSION_PHRASES",
    "BODY_SAFE_KEYWORDS",
    "HIGH_SPECIFICITY_KEYWORDS",
]
