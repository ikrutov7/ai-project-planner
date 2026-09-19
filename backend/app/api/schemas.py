"""API request/response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.domain.enums import TaskStatus
from app.schemas import PlanRead, TaskRead


class TaskCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    assignee: str | None = None
    duration_days: int = Field(..., ge=1)
    predecessor_ids: list[str] = Field(default_factory=list)
    start_date: date | None = None


class TaskPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    assignee: str | None = None
    clear_assignee: bool = False
    duration_days: int | None = Field(default=None, ge=1)
    status: TaskStatus | None = None
    start_date: date | None = None


class MoveTaskRequest(BaseModel):
    new_start_date: date


class DependenciesRequest(BaseModel):
    predecessor_ids: list[str] = Field(default_factory=list)


class BulkChangesRequest(BaseModel):
    assignee: str | None = None
    duration_days: int | None = Field(default=None, ge=1)
    description: str | None = None


class BulkUpdateRequest(BaseModel):
    task_ids: list[str]
    changes: BulkChangesRequest


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None


class ChatMessageOut(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessageOut
    plan: PlanRead
    changes: list[dict] = Field(default_factory=list)
    tool_trace: list[dict] = Field(default_factory=list)
    mode: str = "demo"


class TaskMutationResponse(BaseModel):
    task: TaskRead
    plan: PlanRead


class PlanMutationResponse(BaseModel):
    plan: PlanRead


class ImportResponse(BaseModel):
    plan: PlanRead
    import_report: dict
