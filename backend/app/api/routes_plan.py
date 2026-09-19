"""Plan REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.schemas import PlanMutationResponse
from app.dependencies import get_plan_service
from app.schemas import PlanRead
from app.services.plan_service import PlanService

router = APIRouter(prefix="/api", tags=["plan"])


@router.get("/plan", response_model=PlanRead)
def get_plan(service: PlanService = Depends(get_plan_service)) -> PlanRead:
    return service.get_active_plan()


@router.post("/plan/reset", response_model=PlanRead)
def reset_plan(service: PlanService = Depends(get_plan_service)) -> PlanRead:
    return service.reset_to_seed()
