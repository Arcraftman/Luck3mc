"""Structured logging helpers for the crawler.

Wraps the standard ``logging`` module with a consistent format and an
optional JSON formatter for shipping logs to centralised collectors.
"""

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON for log aggregation pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str, json_output: bool = False) -> logging.Logger:
    """Return a configured logger. Safe to call multiple times per name."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stderr)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
