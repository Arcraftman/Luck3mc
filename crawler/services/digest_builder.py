"""Application service: weekly fiscal/tax subsidy digest + push.

Extracted from ``scripts/weekly_digest.py``. Owns:
  * collecting unique subsidy items from the last ``--days`` of JSONL
  * re-screening every row through the subsidy gate (so pre-filter historical
    rows don't leak into the rollup)
  * grouping hits by source and rendering a Markdown summary
  * pushing via :class:`crawler.notifiers.WebhookNotifier`

The script layer is now a thin CLI that parses args and calls :func:`run`.

No hand-rolled POSTs: delivery is delegated to the shared notifier, exactly
like the daily report service.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

from crawler.config import get_settings
from crawler.notifiers import get_notifier
from crawler.utils.log_config import get_logger

logger = get_logger(__name__)


def collect_week(output_dir: Path, start: date, end: date) -> list[dict]:
    """Return unique subsidy items crawled between ``start`` and ``end``.

    De-duplicates by ``source_url`` (the JSONL sink is append-only) and
    re-screens every row through the subsidy gate so pre-filter rows don't
    leak into the summary.
    """
    # Lazy import keeps this module importable without pulling the pipeline
    # layer at import time (mirrors the original script's deferred import).
    from crawler.pipelines.subsidy_filter import matches_subsidy

    seen: set[str] = set()
    items: list[dict] = []
    if not output_dir.exists():
        return items
    for spider_dir in sorted(output_dir.iterdir()):
        if not spider_dir.is_dir():
            continue
        for jsonl in spider_dir.glob("*.jsonl"):
            try:
                file_date = date.fromisoformat(jsonl.stem)
            except ValueError:
                continue
            if not (start <= file_date <= end):
                continue
            with jsonl.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    url = row.get("source_url", "")
                    if url in seen:
                        continue
                    if not matches_subsidy(
                        title=row.get("title", ""),
                        summary=row.get("summary", ""),
                        content=row.get("content", ""),
                    ):
                        continue
                    seen.add(url)
                    items.append({
                        "title": row.get("title", ""),
                        "url": url,
                        "pub_date": str(row.get("pub_date", "") or ""),
                        "source_site": row.get("source_site", spider_dir.name),
                    })
    return items


THEME_KEYWORDS: list[tuple[str, list[str]]] = [
    ("以旧换新/新能源汽车", ["以旧换新", "新能源汽车", "充电补贴", "购车补贴"]),
    ("留抵/出口退税", ["留抵退税", "出口退税", "退税"]),
    ("研发费用加计扣除", ["研发", "加计扣除", "税收优惠"]),
    ("农业/种粮补贴", ["种粮", "农资", "耕地", "农机", "农业"]),
    ("稳岗就业", ["稳岗", "就业", "扩岗", "社保补贴", "见习"]),
    ("小微/纾困减免", ["小微", "纾困", "减免税", "减免"]),
    ("专项资金/奖补", ["专项", "奖补", "扶持资金", "补助"]),
]


def _theme_summary(items: list[dict]) -> str:
    """One-line prose recap of what the week's subsidies were about."""
    counts: dict[str, int] = {}
    for it in items:
        blob = it.get("title", "") or ""
        for theme, kws in THEME_KEYWORDS:
            if any(k in blob for k in kws):
                counts[theme] = counts.get(theme, 0) + 1
    if not counts:
        return "本周补贴政策主题较为分散，详见下方按来源分类列表。"
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
    parts = [f"{t}（{c}条）" for t, c in top]
    return "本周补贴政策主要集中在：" + "、".join(parts) + "。"


def build_markdown(items: list[dict], start: date, end: date) -> str:
    """Render the weekly digest as Markdown."""
    if not items:
        return (
            f"# 财税补贴政策周报\n\n"
            f"**统计区间**：{start} ~ {end}\n\n"
            f"本周未发现新的财税补贴政策，监测系统运行正常。"
        )

    by_source: dict[str, list[dict]] = {}
    for it in items:
        by_source.setdefault(it["source_site"], []).append(it)

    lines = [
        "# 财税补贴政策周报",
        "",
        f"**统计区间**：{start} ~ {end}",
        f"**本周新发现**：共 **{len(items)}** 条，来自 **{len(by_source)}** 个来源",
        f"**总结**：{_theme_summary(items)}",
        "",
    ]
    for source, rows in sorted(by_source.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"## {source}（{len(rows)} 条）")
        lines.append("")
        for r in rows[:30]:
            pd = f"  ·  {r['pub_date']}" if r["pub_date"] else ""
            title = r["title"].replace("[", "【").replace("]", "】")
            if r["url"]:
                lines.append(f"- [{title}]({r['url']}){pd}")
            else:
                lines.append(f"- {title}{pd}")
        if len(rows) > 30:
            lines.append(f"- … 其余 {len(rows) - 30} 条省略")
        lines.append("")
    return "\n".join(lines)


def run(days: int = 7, dry_run: bool = False, env: str | None = None) -> int:
    """Orchestrate the weekly digest.

    Returns a process exit code (0 on success / dry-run, 1 on push failure).
    ``dry_run`` (or a missing token) prints the Markdown and exits 0 without
    pushing — exactly mirroring the original script's contract.
    """
    cfg = get_settings(env)
    output_dir = cfg.data_dir
    token = cfg.notify.webhook_token or os.environ.get("NOTIFY_WEBHOOK_TOKEN") or ""

    end = date.today()
    start = end - timedelta(days=days - 1)

    items = collect_week(output_dir, start, end)
    markdown = build_markdown(items, start, end)
    title = f"财税补贴政策周报 {start}~{end}"

    logger.info(
        "区间 %s~%s | 命中补贴条目 %d | output_dir=%s",
        start, end, len(items), output_dir,
    )

    if dry_run or not token:
        if not token:
            logger.info("未配置 NOTIFY_WEBHOOK_TOKEN，仅打印（dry-run）。")
        print("\n----- Markdown 预览 -----\n")
        print(markdown)
        return 0

    notifier = get_notifier(cfg.to_notifier_settings())
    ok = notifier.send_markdown(title, markdown)
    logger.info("推送%s", "成功" if ok else "失败")
    return 0 if ok else 1


__all__ = [
    "collect_week",
    "THEME_KEYWORDS",
    "build_markdown",
    "run",
]
