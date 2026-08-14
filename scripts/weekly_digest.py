#!/usr/bin/env python
"""weekly_digest.py — 薄 CLI 入口。

业务核心（读近 N 天 .jsonl → 补贴过滤 → 按来源聚合 → pushplus markdown 推送）
已抽到 ``crawler.services.digest_builder``。本文件只负责解析参数并调用服务，
行为向后兼容：

    python scripts/weekly_digest.py --dry-run        # 预览不推送
    python scripts/weekly_digest.py                  # 开发环境真实推送
    SCRAPY_ENV=production python scripts/weekly_digest.py --days 14
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make the project importable whether run from repo root or elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="财税补贴政策周报")
    parser.add_argument("--days", type=int, default=7,
                        help="统计最近 N 天（默认 7）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印汇总，不推送")
    parser.add_argument("--env", default=os.environ.get("SCRAPY_ENV", "development"),
                        help="SCRAPY_ENV（默认 development）")
    args = parser.parse_args()

    # Honour the chosen environment both for the process and for the service's
    # typed config loader (so the right config/<env>.yaml is read).
    os.environ["SCRAPY_ENV"] = args.env

    from crawler.services import digest_builder

    try:
        return digest_builder.run(days=args.days, dry_run=args.dry_run, env=args.env)
    except RuntimeError as e:
        print(f"[digest] 错误: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
