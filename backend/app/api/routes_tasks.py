"""Task REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.schemas import (
    BulkUpdateRequest,
    DependenciesRequest,
    MoveTaskRequest,
    PlanMutationResponse,
    TaskCreateRequest,
    TaskMutationResponse,
    TaskPatchRequest,
)
from app.dependencies import get_plan_service
from app.schemas import TaskCreate, TaskUpdate
from app.services.plan_service import PlanService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/bulk", response_model=PlanMutationResponse)
def bulk_update(
    body: BulkUpdateRequest,
    service: PlanService = Depends(get_plan_service),
) -> PlanMutationResponse:
    plan = service.bulk_update_tasks(
        body.task_ids,
        assignee=body.changes.assignee,
        duration=body.changes.duration_days,
        description=body.changes.description,
    )
    return PlanMutationResponse(plan=plan)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskMutationResponse)
def create_task(
    body: TaskCreateRequest,
    service: PlanService = Depends(get_plan_service),
) -> TaskMutationResponse:
    assignee_id = service.resolve_assignee_id(body.assignee) if body.assignee else None
    task = service.create_task(
        TaskCreate(
            name=body.name,
            description=body.description,
            assignee_id=assignee_id,
            duration=body.duration_days,
            predecessor_ids=body.predecessor_ids,
            start_date=body.start_date,
        )
    )
    return TaskMutationResponse(task=task, plan=service.get_active_plan())


@router.get("/{task_id}")
def get_task(task_id: str, service: PlanService = Depends(get_plan_service)):
    return service.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskMutationResponse)
def patch_task(
    task_id: str,
    body: TaskPatchRequest,
    service: PlanService = Depends(get_plan_service),
) -> TaskMutationResponse:
    assignee_id = None
    if body.assignee is not None and not body.clear_assignee:
        assignee_id = service.resolve_assignee_id(body.assignee)
    task = service.update_task(
        task_id,
        TaskUpdate(
            name=body.name,
            description=body.description,
            assignee_id=assignee_id,
            clear_assignee=body.clear_assignee,
            duration=body.duration_days,
            status=body.status,
            start_date=body.start_date,
        ),
    )
    return TaskMutationResponse(task=task, plan=service.get_active_plan())


@router.delete("/{task_id}", response_model=PlanMutationResponse)
def delete_task(
    task_id: str,
    service: PlanService = Depends(get_plan_service),
) -> PlanMutationResponse:
    plan = service.delete_task(task_id)
    return PlanMutationResponse(plan=plan)


@router.post("/{task_id}/move", response_model=TaskMutationResponse)
def move_task(
    task_id: str,
    body: MoveTaskRequest,
    service: PlanService = Depends(get_plan_service),
) -> TaskMutationResponse:
    task = service.move_task(task_id, body.new_start_date)
    return TaskMutationResponse(task=task, plan=service.get_active_plan())


@router.put("/{task_id}/dependencies", response_model=TaskMutationResponse)
def set_dependencies(
    task_id: str,
    body: DependenciesRequest,
    service: PlanService = Depends(get_plan_service),
) -> TaskMutationResponse:
    task = service.set_dependencies(task_id, body.predecessor_ids)
    return TaskMutationResponse(task=task, plan=service.get_active_plan())
