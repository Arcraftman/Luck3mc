from sqlalchemy import create_engine, inspect

from crawler.commands.monitor import ensure_database_schema


def test_monitor_initializes_empty_database(tmp_path):
    database = tmp_path / "crawler.db"
    url = f"sqlite:///{database}"

    ensure_database_schema(url)
    assert set(inspect(create_engine(url)).get_table_names()) >= {
        "crawled_urls",
        "tax_records",
    }


def test_monitor_database_initialization_is_idempotent(tmp_path):
    url = f"sqlite:///{tmp_path / 'crawler.db'}"
    ensure_database_schema(url)
    ensure_database_schema(url)
