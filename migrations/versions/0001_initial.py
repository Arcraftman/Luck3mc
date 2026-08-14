"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tax_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_site", sa.String(length=128), nullable=False),
        sa.Column("doc_number", sa.String(length=64), nullable=True),
        sa.Column("pub_date", sa.String(length=20), nullable=True),
        sa.Column("effective_date", sa.String(length=20), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("issuing_authority", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=128), nullable=True),
        sa.Column("business_type", sa.String(length=128), nullable=True),
        sa.Column("processing_time_limit", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url", "item_type", name="uq_tax_records_url_type"),
    )
    op.create_table(
        "crawled_urls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_site", sa.String(length=128), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=True),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url", "source_site", name="uq_crawled_urls"),
    )


def downgrade() -> None:
    op.drop_table("crawled_urls")
    op.drop_table("tax_records")
