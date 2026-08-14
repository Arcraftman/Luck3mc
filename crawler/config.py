"""Typed application configuration.

A thin, dependency-inverted façade over :mod:`crawler.utils.config_loader`.

The ``config/*.yaml`` files remain the operator-tunable source of truth; this
module reads them through :func:`crawler.utils.config_loader.load_config` and
shapes the result into immutable :func:`dataclasses` so the rest of the code
(base/ production settings, the ``scripts/`` CLIs, and the new
``crawler/services`` application layer) no longer reaches into raw dicts or
re-implements the ``storage.output_dir`` → ``Path`` resolution logic.

Backwards compatibility:
  * The old :mod:`crawler.settings.base` module and the ``scripts/`` keep
    working untouched — they may still call ``load_config()`` directly.
  * The YAML structure (``scraping`` / ``proxy`` / ``storage`` / ``logging`` /
    ``notify`` / ``monitor``) is **not** changed; only *read* here.
  * Plaintext ``notify.webhook_token`` is preserved exactly (the task forbids
    altering those values).

The :func:`get_settings` singleton caches the parsed :class:`AppConfig` so the
YAML is only read once per process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crawler.utils.config_loader import PROJECT_ROOT, load_config


# ---------------------------------------------------------------------------
# Typed sub-configs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ScrapeConfig:
    """Politeness / concurrency knobs (mirrors ``scraping:`` in YAML)."""

    robots_obey: bool = True
    concurrent_requests: int = 16
    download_delay: float = 1.0
    autothrottle: bool = True

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> ScrapeConfig:
        scrape = (cfg.get("scraping") or {}) if cfg else {}
        return cls(
            robots_obey=bool(scrape.get("robots_obey", cls.robots_obey)),
            concurrent_requests=int(scrape.get("concurrent_requests", cls.concurrent_requests)),
            download_delay=float(scrape.get("download_delay", cls.download_delay)),
            autothrottle=bool(scrape.get("autothrottle", cls.autothrottle)),
        )


@dataclass(frozen=True)
class StorageConfig:
    """Where crawled items / the dedup ledger live (``storage:`` in YAML)."""

    database_url: str = ""
    output_dir: str = "data"
    # Project root used to anchor *relative* output_dir values. Kept out of the
    # repr so it doesn't clutter logs; it is an immutable module constant.
    root: Path = field(default=PROJECT_ROOT, repr=False)

    @property
    def output_path(self) -> Path:
        """Absolute output directory.

        Relative ``output_dir`` values are resolved against :attr:`root`
        (mirroring ``config_loader.apply_config`` / ``JsonLinesExportPipeline``
        so scripts and the crawler agree on where JSONL lands).
        """
        p = Path(self.output_dir)
        return p if p.is_absolute() else self.root / p

    @classmethod
    def from_config(cls, cfg: dict[str, Any], root: Path = PROJECT_ROOT) -> StorageConfig:
        storage = (cfg.get("storage") or {}) if cfg else {}
        return cls(
            database_url=str(storage.get("database_url", "") or ""),
            output_dir=str(storage.get("output_dir") or "data"),
            root=root,
        )


@dataclass(frozen=True)
class NotifyConfig:
    """Notification backend settings (``notify:`` in YAML).

    ``webhook_token`` is carried through verbatim — the project deliberately
    keeps the pushplus token in the YAML for now, so we never mutate it here.
    """

    enabled: bool = False
    backend: str = "webhook"
    webhook_url: str = ""
    webhook_kind: str = "generic"
    webhook_token: str = ""
    template: str = "markdown"

    def as_notifier_settings(self) -> dict[str, str]:
        """Shape into the mapping consumed by :func:`crawler.notifiers.get_notifier`."""
        return {
            "NOTIFY_BACKEND": self.backend,
            "NOTIFY_WEBHOOK_KIND": self.webhook_kind,
            "NOTIFY_WEBHOOK_TOKEN": self.webhook_token,
            "NOTIFY_WEBHOOK_URL": self.webhook_url,
        }

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> NotifyConfig:
        notify = (cfg.get("notify") or {}) if cfg else {}
        return cls(
            enabled=bool(notify.get("enabled", cls.enabled)),
            backend=str(notify.get("backend", cls.backend) or "webhook"),
            webhook_url=str(notify.get("webhook_url", "") or ""),
            webhook_kind=str(notify.get("webhook_kind", cls.webhook_kind) or "generic"),
            webhook_token=str(notify.get("webhook_token", "") or ""),
            template=cls.template,
        )


@dataclass(frozen=True)
class AppConfig:
    """Top-level, immutable view of the externalised configuration."""

    scrape: ScrapeConfig
    storage: StorageConfig
    notify: NotifyConfig
    # Raw YAML dict, kept for escape hatches / forward-compat. Excluded from repr.
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def data_dir(self) -> Path:
        """Absolute directory crawled JSONL is written to / read from."""
        return self.storage.output_path

    def to_notifier_settings(self) -> dict[str, str]:
        """Delegate to :meth:`NotifyConfig.as_notifier_settings`."""
        return self.notify.as_notifier_settings()

    @classmethod
    def load(cls, env: str | None = None) -> AppConfig:
        """Build an :class:`AppConfig` from ``config/<env>.yaml``.

        Degrades to defaults when the file is missing or PyYAML is absent
        (``load_config`` returns ``{}``), so callers never crash on config.
        """
        cfg = load_config(env) or {}
        return cls(
            scrape=ScrapeConfig.from_config(cfg),
            storage=StorageConfig.from_config(cfg),
            notify=NotifyConfig.from_config(cfg),
            raw=cfg,
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------
_SETTINGS: AppConfig | None = None


def get_settings(env: str | None = None) -> AppConfig:
    """Return the cached :class:`AppConfig` (loading it on first call).

    Pass an explicit ``env`` to force a re-read (e.g. tests). When omitted, the
    cached instance is reused for the whole process.
    """
    global _SETTINGS
    if _SETTINGS is not None and env is None:
        return _SETTINGS
    _SETTINGS = AppConfig.load(env)
    return _SETTINGS


def reload_settings(env: str | None = None) -> AppConfig:
    """Discard any cached config and re-load (handy for tests / env switches)."""
    global _SETTINGS
    _SETTINGS = AppConfig.load(env)
    return _SETTINGS


__all__ = [
    "AppConfig",
    "NotifyConfig",
    "StorageConfig",
    "ScrapeConfig",
    "get_settings",
    "reload_settings",
]
