"""Pydantic schemas for request/response validation."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PolicyIn(BaseModel):
    title: str
    source_url: str
    pub_date: str = ""
    pub_datetime: str = ""
    doc_number: str = ""
    category: str = ""
    issuing_authority: str = ""
    source_site: str = ""
    content: str = ""
    subsidy: bool = False


class PolicyOut(PolicyIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crawled_at: datetime | None = None
    updated_at: datetime | None = None


class ReportIn(BaseModel):
    title: str
    content_md: str
    date: str = ""
    spiders: str = ""


class ReportOut(ReportIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
