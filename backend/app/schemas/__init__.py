"""Pydantic schemas for API / service boundaries."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import TaskStatus


class AssigneeCreate(BaseModel):
    name: str = Field(..., min_length=1)


class AssigneeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime


class DependencyCreate(BaseModel):
    predecessor_id: str = Field(..., min_length=1)


class DependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    predecessor_id: str


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    assignee_id: str | None = None
    start_date: date | None = None
    duration: int = Field(..., ge=1)
    status: TaskStatus = TaskStatus.PENDING
    predecessor_ids: list[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    assignee_id: str | None = None
    start_date: date | None = None
    duration: int | None = Field(default=None, ge=1)
    status: TaskStatus | None = None
    clear_assignee: bool = False


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    name: str
    description: str
    assignee_id: str | None
    start_date: date
    duration: int
    end_date: date
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    predecessor_ids: list[str] = Field(default_factory=list)


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1)
    project_start: date


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    project_start: date
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskRead] = Field(default_factory=list)
    assignees: list[AssigneeRead] = Field(default_factory=list)
