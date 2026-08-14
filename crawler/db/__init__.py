"""Database access layer (SQLAlchemy).

Importing this package registers all models on the shared declarative base.
Use :mod:`crawler.db.session` to obtain an engine / session, and the
``createdb`` Scrapy command (``scrapy createdb``) to initialise schemas.
"""

from crawler.db import models  # noqa: F401 - ensure models are registered
from crawler.db.base import Base
from crawler.db.session import get_engine, get_sessionmaker, init_db

__all__ = ["Base", "models", "get_engine", "get_sessionmaker", "init_db"]
