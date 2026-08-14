"""Policy list / detail endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..db import get_db

router = APIRouter(prefix="/api", tags=["policies"])


@router.get("/policies", response_model=list[schemas.PolicyOut])
def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    q: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.get_policies(db, skip=skip, limit=limit, q=q, source=source)


@router.get("/policies/{pid}", response_model=schemas.PolicyOut)
def get_policy(pid: int, db: Session = Depends(get_db)):
    obj = crud.get_policy(db, pid)
    if not obj:
        raise HTTPException(404, "policy not found")
    return obj
