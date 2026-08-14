"""DeepSeek report list endpoint."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..db import get_db

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports", response_model=list[schemas.ReportOut])
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    date: Optional[str] = Query(None, description="按报告日期精确过滤，如 2026-08-12"),
    source: Optional[str] = Query(None, description="按来源官网(爬虫名)过滤，如 mof_fgk"),
    db: Session = Depends(get_db),
):
    return crud.get_reports(db, skip=skip, limit=limit, date=date, source=source)
