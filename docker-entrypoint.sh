#!/bin/sh
# Entrypoint for the tax-policy-crawler image.
# - ensures the de-duplication DB schema exists (idempotent)
# - dispatches to monitor / crawl / createdb / shell, or a raw command
set -eu

DATA_DIR="${DATA_DIR:-/var/lib/crawler/data}"
mkdir -p "$DATA_DIR"

# Persistent de-duplication requires a real database. `scrapy createdb` runs
# Alembic migrations; if the schema is already at head it is a safe no-op,
# so running it on every start keeps the container self-bootstrapping.
if [ -n "${DATABASE_URL:-}" ]; then
    echo "[entrypoint] ensuring database schema (scrapy createdb)..."
    scrapy createdb || echo "[entrypoint] WARN: createdb failed; continuing without DB"
fi

case "${1:-monitor}" in
    monitor)
        exec scrapy monitor
        ;;
    crawl)
        shift
        exec scrapy crawl "$@"
        ;;
    createdb)
        exec scrapy createdb
        ;;
    shell)
        exec scrapy shell
        ;;
    *)
        exec "$@"
        ;;
esac
