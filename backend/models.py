"""ORM models: crawled policies and generated DeepSeek reports."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql.functions import func

from .db import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), index=True, nullable=False)
    source_url = Column(String(1024), unique=True, index=True, nullable=False)
    pub_date = Column(String(32), index=True, default="")
    issuing_authority = Column(String(256), default="")
    source_site = Column(String(256), default="")
    content = Column(Text, default="")
    subsidy = Column(Boolean, default=False)
    crawled_at = Column(DateTime, server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    content_md = Column(Text, nullable=False)
    date = Column(String(32), index=True, default="")
    spiders = Column(String(512), default="")
    created_at = Column(DateTime, server_default=func.now())
