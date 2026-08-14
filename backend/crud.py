"""Database access helpers (create / read / upsert)."""
from typing import Optional

from sqlalchemy.orm import Session

from . import models, schemas


def upsert_policy(db: Session, p: schemas.PolicyIn):
    existing = (
        db.query(models.Policy)
        .filter(models.Policy.source_url == p.source_url)
        .first()
    )
    if existing:
        # Update mutable fields; keep the original id / crawled_at.
        existing.title = p.title
        existing.pub_date = p.pub_date
        existing.issuing_authority = p.issuing_authority
        existing.source_site = p.source_site
        existing.content = p.content
        existing.subsidy = p.subsidy
        db.commit()
        db.refresh(existing)
        return existing, False
    obj = models.Policy(**p.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj, True


def create_report(db: Session, r: schemas.ReportIn):
    obj = models.Report(**r.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_policies(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    source: Optional[str] = None,
):
    query = db.query(models.Policy)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.Policy.title.ilike(like))
            | (models.Policy.content.ilike(like))
        )
    if source:
        query = query.filter(models.Policy.source_site == source)
    return (
        query.order_by(models.Policy.crawled_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_policy(db: Session, pid: int):
    return db.query(models.Policy).filter(models.Policy.id == pid).first()


def get_reports(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    date: Optional[str] = None,
    source: Optional[str] = None,
):
    """List generated reports, newest first.

    ``date``   exact-match on the report's date string (e.g. ``2026-08-12``).
    ``source`` substring match on the stored ``spiders`` blob, so a single daily
             report that covers several official websites can be filtered down
             to one site (e.g. ``mof_fgk`` -> 财政部).
    """
    query = db.query(models.Report)
    if date:
        query = query.filter(models.Report.date == date)
    if source:
        query = query.filter(models.Report.spiders.contains(source))
    return (
        query.order_by(models.Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
