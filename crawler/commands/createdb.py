"""Scrapy command: initialise the crawler database.

Usage:
    scrapy createdb            # uses DATABASE_URL from the environment/settings
    DATABASE_URL=sqlite:///data/crawler.db scrapy createdb

It runs the Alembic migrations when Alembic is available, otherwise falls
back to ``Base.metadata.create_all`` so the schema still gets created.
"""

import logging
import os
import sys
from pathlib import Path

from scrapy.commands import ScrapyCommand

logger = logging.getLogger(__name__)


class Command(ScrapyCommand):
    requires_project = True
    default_settings = {"LOG_ENABLED": False}

    def syntax(self) -> str:
        return "[options]"

    def short_desc(self) -> str:
        return "Initialise the crawler database (run migrations / create tables)"

    def run(self, args, opts) -> None:
        if self.settings is None:
            logger.error("Settings are not available; cannot create the database.")
            sys.exit(1)

        database_url = self.settings.get("DATABASE_URL")
        if not database_url:
            logger.error(
                "DATABASE_URL is not set. Export it (or set it in config YAML) "
                "before running `scrapy createdb`."
            )
            sys.exit(1)

        # Prefer Alembic migrations for a controlled, reviewable schema.
        try:
            from alembic import command as alembic_cmd
            from alembic.config import Config

            # createdb.py lives at <project>/crawler/commands/createdb.py, so
            # parents[2] is the project root that holds alembic.ini / migrations.
            project_root = Path(__file__).resolve().parents[2]
            ini = project_root / "alembic.ini"
            if ini.exists():
                cfg = Config(str(ini))
                cfg.set_main_option("script_location", str(project_root / "migrations"))
                os.environ["DATABASE_URL"] = database_url
                alembic_cmd.upgrade(cfg, "head")
                logger.info("Database migrated to head at %s", database_url)
                return
        except ImportError:
            logger.warning("Alembic not installed; falling back to create_all.")

        # Fallback: idempotent table creation via the ORM metadata.
        from crawler.db.session import get_engine, init_db

        engine = get_engine(database_url)
        init_db(engine)
        logger.info("Database initialised (create_all) at %s", database_url)
