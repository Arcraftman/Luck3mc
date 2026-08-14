"""Load externalised YAML configuration into Scrapy settings.

The ``config/*.yaml`` files are the operator-tunable source of truth for
non-secret runtime parameters (politeness, proxy pool, storage, logging).
Environment variables of the form ``${VAR}`` inside the YAML are expanded
from ``os.environ`` so secrets never live in the committed config files.

Selected file: ``config/<env>.yaml`` where ``<env>`` = ``SCRAPY_ENV``, or the
explicit path in ``STAT_CONFIG_FILE``. This matches the same environment that
selects the settings module (see ``crawler/settings/__init__.py``).

Precedence: base defaults  <  YAML config  <  environment-specific Python
overrides (development / production / testing modules import ``*`` from base
and then override).
"""

import os
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Mapping from nested YAML keys -> Scrapy setting name.
_CONFIG_MAP = {
    ("scraping", "robots_obey"): "ROBOTSTXT_OBEY",
    ("scraping", "concurrent_requests"): "CONCURRENT_REQUESTS",
    ("scraping", "download_delay"): "DOWNLOAD_DELAY",
    ("scraping", "autothrottle"): "AUTOTHROTTLE_ENABLED",
    ("proxy", "pool"): "PROXY_POOL",
    ("proxy", "api_url"): "PROXY_API_URL",
    ("storage", "database_url"): "DATABASE_URL",
    ("storage", "output_dir"): "OUTPUT_DIR",
    ("logging", "level"): "LOG_LEVEL",
    ("logging", "json"): "LOG_JSON",
    ("notify", "enabled"): "NOTIFY_ENABLED",
    ("notify", "backend"): "NOTIFY_BACKEND",
    ("notify", "webhook_url"): "NOTIFY_WEBHOOK_URL",
    ("notify", "webhook_kind"): "NOTIFY_WEBHOOK_KIND",
    ("notify", "webhook_token"): "NOTIFY_WEBHOOK_TOKEN",
    ("monitor", "spiders"): "MONITOR_SPIDERS",
    ("monitor", "subsidy_keywords"): "SUBSIDY_KEYWORDS",
    ("backend", "ingest_url"): "BACKEND_INGEST_URL",
    ("backend", "ingest_token"): "BACKEND_INGEST_TOKEN",
    ("backend", "sink_enabled"): "BACKEND_SINK_ENABLED",
}

# Keys also exposed as environment variables so existing utils (proxy
# rotator, storage) keep working unchanged. Explicit env vars win.
_ENV_BRIDGE = ("PROXY_POOL", "PROXY_API_URL", "DATABASE_URL")


def _expand(value: Any) -> Any:
    """Recursively replace ``${VAR}`` with ``os.environ[VAR]`` (or '')."""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def config_path(env: str | None = None) -> Path:
    """Resolve which YAML file to load."""
    env = (env or os.environ.get("SCRAPY_ENV", "development")).lower()
    explicit = os.environ.get("STAT_CONFIG_FILE")
    if explicit:
        return Path(explicit)
    name = "development"
    if env == "production":
        name = "production"
    elif env == "testing":
        name = "testing"
    return PROJECT_ROOT / "config" / f"{name}.yaml"


_DOTENV_LOADED = False


def _ensure_dotenv() -> None:
    """Best-effort load of the project-root ``.env`` into ``os.environ``.

    Only sets keys that are absent, so an explicitly exported environment
    variable always wins. This lets ``${VAR}`` references inside
    ``config/*.yaml`` resolve secrets that live in ``.env`` (which is
    git-ignored) instead of committing them in plaintext.
    """
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    p = PROJECT_ROOT / ".env"
    if not p.exists():
        return
    try:
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        return


def load_config(env: str | None = None) -> dict[str, Any]:
    """Read and env-expand the YAML config. Returns ``{}`` if unavailable.

    Degrades gracefully (empty dict) when PyYAML is missing or the file is
    absent, so the crawler still runs on hardcoded defaults.
    """
    _ensure_dotenv()
    path = config_path(env)
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return {}
    return _expand(data)


def apply_config(settings: dict[str, Any], env: str | None = None) -> dict[str, Any]:
    """Merge YAML config into a settings dict (e.g. module ``globals()``).

    Precedence (lowest to highest):
        base defaults  <  YAML config  <  explicit env var (bridged keys)
        <  environment-specific Python overrides (applied after this call)

    An *empty* YAML value (``None`` / ``""``) is deliberately skipped so it can
    never clobber a non-empty value that was already established by a base
    default or a previously-read environment variable. Only a YAML value that
    actually says something overrides the existing setting.

    Returns the dict (mutated in place).
    """
    config = load_config(env)
    if not config:
        return settings

    for (section, key), setting in _CONFIG_MAP.items():
        if section in config and key in config[section]:
            value = config[section][key]
            # Skip empties: they must not wipe an existing non-empty value
            # (e.g. DATABASE_URL already resolved from the shell env in base.py).
            if value in (None, ""):
                continue
            settings[setting] = value

    # Bridge to os.environ. Explicit env vars win for the bridged keys so
    # operators can always override at runtime; otherwise a non-empty setting
    # is exported so downstream env readers keep working unchanged.
    for setting in _ENV_BRIDGE:
        env_val = os.environ.get(setting)
        if env_val:
            settings[setting] = env_val
        elif settings.get(setting):
            os.environ.setdefault(setting, str(settings[setting]))

    # Normalise OUTPUT_DIR: resolve relative paths against the project root.
    out = settings.get("OUTPUT_DIR")
    if out:
        p = Path(str(out))
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        settings["OUTPUT_DIR"] = p

    return settings
