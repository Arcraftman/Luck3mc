"""Smoke test that settings load for each environment.

Each call reloads ``base`` (which re-applies the YAML config for the active
env) and the target env module so the values reflect the chosen environment.
"""

import importlib
import os


def _load_env(env: str):
    os.environ["SCRAPY_ENV"] = env
    import crawler.settings as s
    import crawler.settings.base as base

    mod = importlib.import_module(f"crawler.settings.{env}")
    importlib.reload(base)   # re-run apply_config() for the new env
    importlib.reload(mod)    # pick up fresh base values
    importlib.reload(s)      # re-run __init__ -> from .<env> import *
    return s


def test_development_settings_load():
    s = _load_env("development")
    assert s.SCRAPY_ENV == "development"
    assert s.ROBOTSTXT_OBEY is True


def test_production_settings_load():
    s = _load_env("production")
    assert s.SCRAPY_ENV == "production"
    assert s.CONCURRENT_REQUESTS >= 32


def test_testing_settings_load():
    s = _load_env("testing")
    assert s.SCRAPY_ENV == "testing"
    assert s.ROBOTSTXT_OBEY is False
