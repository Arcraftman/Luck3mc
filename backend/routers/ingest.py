"""Ingest endpoints called by the crawler (authenticated by X-Token)."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import INGEST_TOKEN
from ..db import get_db
from ..events import bus

router = APIRouter(prefix="/api", tags=["ingest"])


async def verify_token(x_token: str = Header(None)):
    if not x_token or x_token != INGEST_TOKEN:
        raise HTTPException(status_code=403, detail="invalid ingest token")


@router.post("/ingest/policy", status_code=200)
async def ingest_policy(
    p: schemas.PolicyIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    obj, created = crud.upsert_policy(db, p)
    if created:
        await bus.broadcast(
            {"type": "policy", "data": schemas.PolicyOut.model_validate(obj).model_dump(mode="json")}
        )
    return {"ok": True, "created": created}


@router.post("/ingest/report", status_code=200)
async def ingest_report(
    r: schemas.ReportIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    obj = crud.create_report(db, r)
    await bus.broadcast(
        {"type": "report", "data": schemas.ReportOut.model_validate(obj).model_dump(mode="json")}
    )
    return {"ok": True}
