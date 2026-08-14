"""Engine / session helpers for the crawler database."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from crawler.db.base import Base


def get_engine(database_url: str, **kwargs) -> Engine:
    """Create a SQLAlchemy engine.

    ``pool_pre_ping`` keeps long-lived connections healthy (important for
    server-side production runs against PostgreSQL).
    """
    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
        **kwargs,
    )


def get_sessionmaker(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db(engine: Engine) -> None:
    """Create all tables via the declarative metadata (idempotent)."""
    Base.metadata.create_all(engine)
