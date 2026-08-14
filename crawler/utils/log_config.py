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

def init_logging(
    level: str | int = "INFO",
    log_file: str | None = None,
    json_output: bool = False,
) -> None:
    """按当前 Scrapy 环境的 LOG_* 设置初始化 root logger。

    调用方（monitor / createdb）应从 settings 把 ``LOG_LEVEL`` / ``LOG_FILE``
    传进来，从而真正由 ``SCRAPY_ENV`` 决定日志行为：
      * development → DEBUG、落盘 logs/crawler.log
      * production  → INFO、落盘 logs/crawler.log
      * testing     → WARNING、不落盘（LOG_FILE=None）
    幂等：重复调用不会叠加 handler。
    """
    root = logging.getLogger()
    if root.handlers:
        return

    # 把 Scrapy 的 "DEBUG/INFO/WARNING" 字符串转成 logging 常量。
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
    root.setLevel(level)

    fmt = JsonFormatter() if json_output else logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    # 控制台（stderr）
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    # 落盘（仅当 LOG_FILE 有值；testing 环境传 None 即跳过）
    if log_file:
        try:
            from pathlib import Path
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except Exception:
            pass

