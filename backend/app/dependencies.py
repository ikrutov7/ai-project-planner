"""FastAPI dependency injection."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import PlanRepository
from app.services.plan_service import PlanService


def get_plan_service(db: Session = Depends(get_db)) -> Generator[PlanService, None, None]:
    repo = PlanRepository(db)
    service = PlanService(repo)
    try:
        yield service
        db.commit()
    except Exception:
        db.rollback()
        raise
