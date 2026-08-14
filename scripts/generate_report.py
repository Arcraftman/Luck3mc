#!/usr/bin/env python3
"""generate_report.py — 薄 CLI 入口。

业务核心（读 .jsonl → 调 DeepSeek → 拼报告 → pushplus markdown 推送）已抽到
``crawler.services.report_generator``。本文件只负责解析命令行参数并展示结果，
不再包含任何抓取 / 推送逻辑，确保行为向后兼容：

    python scripts/generate_report.py                         # 默认今天、全部 spider
    python scripts/generate_report.py --date 2026-08-11       # 指定日期
    python scripts/generate_report.py --spiders mof_fgk most_news
    python scripts/generate_report.py --no-push --out report.md   # 只生成不推送

    # 直接推送一个已生成的 .md 报告（不再调 DeepSeek），例如：
    python scripts/generate_report.py --push-file report_2026-08-12.md
    python scripts/generate_report.py --push-file report_2026-08-12.md --no-push  # 仅演练
"""
from __future__ import annotations

import argparse
import datetime

# Make the project importable whether run from repo root or elsewhere.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Importing the service is deferred into ``main()`` so that ``--help`` works
# without importing the world (and without touching the network).


def main() -> None:
    ap = argparse.ArgumentParser(
        description="基于当日爬取的 .jsonl 原文，调用 DeepSeek 生成政策报告并推送。",
    )
    ap.add_argument("--date", default=datetime.date.today().isoformat(),
                    help="统计日期（默认今天）")
    ap.add_argument("--spiders", nargs="*", default=None,
                    help="只聚合指定 spider 目录（默认全部）")
    ap.add_argument("--max-items", type=int, default=30,
                    help="最多读取的条目数（默认 30）")
    ap.add_argument("--no-push", action="store_true",
                    help="只生成报告，不推送")
    ap.add_argument("--no-save", action="store_true",
                    help="不写 report_<date>.md 文件（默认会写）")
    ap.add_argument("--out", default=None,
                    help="将报告写入该文件（默认 report_<date>.md）")
    ap.add_argument("--push-file", default=None,
                    help="直接推送一个已生成的 .md 报告文件（不再调 DeepSeek）")
    args = ap.parse_args()

    from crawler.services import report_generator

    # 模式 A：直接推送已有 .md 报告（不重新生成）。
    if args.push_file:
        try:
            res = report_generator.push_file(
                args.push_file, no_push=args.no_push
            )
        except RuntimeError as e:
            print(f"[generate_report] 错误: {e}")
            sys.exit(1)
        if args.no_push:
            print(f"[generate_report] 演练（不推送）: {res['path']} ({res['chars']} 字)")
            return
        print(f"[generate_report] 已推送 {res['path']} "
              f"({'成功' if res['pushed'] else '失败'})")
        return

    # 模式 B：生成（今天/指定日期）→ 写 report_<date>.md → 推送该文件。
    try:
        summary = report_generator.run(
            date_str=args.date,
            spiders=args.spiders,
            max_items=args.max_items,
            no_push=args.no_push,
            out=args.out,
            no_save=args.no_save,
        )
    except RuntimeError as e:
        print(f"[generate_report] 错误: {e}")
        sys.exit(1)

    if summary["items"] == 0:
        print(f"[generate_report] 没有找到 {summary['date']} 的 jsonl 数据，退出。")
        return

    if summary["out"]:
        print(f"[generate_report] 报告已写入 {summary['out']}")

    if args.no_push:
        print("[generate_report] --no-push，跳过推送。")
        return

    print(f"[generate_report] pushplus 推送{'成功' if summary['pushed'] else '失败'}")


if __name__ == "__main__":
    main()
