# syntax=docker/dockerfile:1
#
# Tax Policy Crawler — container image.
# Pure-Python Scrapy project; runs unchanged on Linux.
#
# Build (default: includes headless Chromium for the JS-rendered spiders):
#   docker build -t tax-policy-crawler:latest .
# Static-only (smaller image, drops chinatax_fgk / mof_fgk / tax_12366 / miit_zjtx):
#   docker build --build-arg INSTALL_CHROMIUM=false -t tax-policy-crawler:latest .

ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SCRAPY_ENV=production \
    APP_HOME=/app

WORKDIR /app

# Build/runtime essentials. Some transitive wheels may compile from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (pinned in requirements/lock.txt for reproducibility).
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# Optional: headless Chromium for JavaScript-rendered spiders.
# chinatax_fgk (the core tax-policy entry), mof_fgk, tax_12366, miit_zjtx
# need a browser; the other 6 spiders are plain static HTML and do not.
ARG INSTALL_CHROMIUM=true
RUN if [ "$INSTALL_CHROMIUM" = "true" ]; then \
        pip install --no-cache-dir scrapy-playwright \
        && playwright install --with-deps chromium; \
    fi

# Application code.
COPY . .

# Dedicated non-root user. The data dir is created here so a named volume
# mounted over it inherits crawler ownership (writable without root).
RUN useradd --create-home --uid 1000 crawler \
    && mkdir -p /var/lib/crawler/data \
    && chown -R crawler:crawler /app /var/lib/crawler/data

USER crawler
ENV DATA_DIR=/var/lib/crawler/data

VOLUME ["/var/lib/crawler/data"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["monitor"]
