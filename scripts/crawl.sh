#!/usr/bin/env bash
# Run a spider inside the container or locally.
# Usage: ./scripts/crawl.sh [spider_name] [extra scrapy args...]
set -euo pipefail

SPIDER="${1:-${CRAWL_SPIDER:-gov_policy_root}}"
shift || true

echo ">> Running spider: ${SPIDER} (SCRAPY_ENV=${SCRAPY_ENV:-development})"
exec scrapy crawl "${SPIDER}" "$@"
