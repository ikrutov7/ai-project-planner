"""MCP tool schemas and handlers over PlanService."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.domain.errors import DomainError
from app.domain.enums import TaskStatus
from app.schemas import TaskCreate, TaskUpdate
from app.services.plan_service import PlanService


class GetTaskInput(BaseModel):
    task_id: str


class SearchTasksInput(BaseModel):
    query: str = ""


class CreateTaskInput(BaseModel):
    name: str
    description: str = ""
    assignee: str | None = None
    duration_days: int = Field(..., ge=1)
    predecessor_ids: list[str] = Field(default_factory=list)


class UpdateTaskInput(BaseModel):
    task_id: str
    name: str | None = None
    description: str | None = None


class DeleteTaskInput(BaseModel):
    task_id: str


class MoveTaskInput(BaseModel):
    task_id: str
    new_start_date: date


class SetDependenciesInput(BaseModel):
    task_id: str
    predecessor_ids: list[str] = Field(default_factory=list)


class SetAssigneeInput(BaseModel):
    task_id: str
    assignee: str | None = None


class SetDurationInput(BaseModel):
    task_id: str
    duration_days: int = Field(..., ge=1)


class BulkChanges(BaseModel):
    assignee: str | None = None
    duration_days: int | None = Field(default=None, ge=1)
    description: str | None = None


class BulkUpdateInput(BaseModel):
    task_ids: list[str]
    changes: BulkChanges


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


def _ok(data: Any, plan_version: int) -> dict[str, Any]:
    return {"success": True, "data": data, "plan_version": plan_version}


def _fail(exc: DomainError) -> dict[str, Any]:
    return {"success": False, "error": exc.to_dict()}


class MCPServer:
    """In-process MCP tool registry."""

    def __init__(self, plan_service: PlanService) -> None:
        self._svc = plan_service
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "get_plan": self._get_plan,
            "get_task": self._get_task,
            "search_tasks": self._search_tasks,
            "create_task": self._create_task,
            "update_task": self._update_task,
            "delete_task": self._delete_task,
            "move_task": self._move_task,
            "set_dependencies": self._set_dependencies,
            "set_assignee": self._set_assignee,
            "set_duration": self._set_duration,
            "bulk_update_tasks": self._bulk_update_tasks,
        }

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="get_plan",
                description="Return the full active plan snapshot with tasks and assignees.",
                input_schema={"type": "object", "properties": {}},
            ),
            ToolSpec(
                name="get_task",
                description="Get one task by id.",
                input_schema=GetTaskInput.model_json_schema(),
            ),
            ToolSpec(
                name="search_tasks",
                description="Search tasks by id/name/description/assignee substring.",
                input_schema=SearchTasksInput.model_json_schema(),
            ),
            ToolSpec(
                name="create_task",
                description="Create a new task in the active plan.",
                input_schema=CreateTaskInput.model_json_schema(),
            ),
            ToolSpec(
                name="update_task",
                description="Update task name and/or description.",
                input_schema=UpdateTaskInput.model_json_schema(),
            ),
            ToolSpec(
                name="delete_task",
                description="Delete a task and clean dependent edges.",
                input_schema=DeleteTaskInput.model_json_schema(),
            ),
            ToolSpec(
                name="move_task",
                description="Soft-pin task start date (YYYY-MM-DD); scheduler clamps to FS earliest.",
                input_schema=MoveTaskInput.model_json_schema(),
            ),
            ToolSpec(
                name="set_dependencies",
                description="Replace predecessor list for a task (Finish-to-Start).",
                input_schema=SetDependenciesInput.model_json_schema(),
            ),
            ToolSpec(
                name="set_assignee",
                description="Assign or clear assignee (by name or id).",
                input_schema=SetAssigneeInput.model_json_schema(),
            ),
            ToolSpec(
                name="set_duration",
                description="Change task duration in working days.",
                input_schema=SetDurationInput.model_json_schema(),
            ),
            ToolSpec(
                name="bulk_update_tasks",
                description="Apply the same field changes to many tasks atomically.",
                input_schema=BulkUpdateInput.model_json_schema(),
            ),
        ]

    def openai_tools(self) -> list[dict[str, Any]]:
        tools = []
        for spec in self.list_tools():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.input_schema,
                    },
                }
            )
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        handler = self._handlers.get(name)
        if handler is None:
            return {
                "success": False,
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Unknown tool: {name}",
                    "details": {},
                },
            }
        try:
            return handler(arguments or {})
        except DomainError as exc:
            return _fail(exc)
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL",
                    "message": str(exc),
                    "details": {},
                },
            }

    def _plan_version(self) -> int:
        return self._svc.get_active_plan().version

    def _get_plan(self, _args: dict[str, Any]) -> dict[str, Any]:
        plan = self._svc.get_active_plan()
        return _ok(plan.model_dump(mode="json"), plan.version)

    def _get_task(self, args: dict[str, Any]) -> dict[str, Any]:
        data = GetTaskInput.model_validate(args)
        task = self._svc.get_task(data.task_id)
        return _ok(task.model_dump(mode="json"), self._plan_version())

    def _search_tasks(self, args: dict[str, Any]) -> dict[str, Any]:
        data = SearchTasksInput.model_validate(args)
        tasks = self._svc.search_tasks(data.query)
        return _ok(
            [t.model_dump(mode="json") for t in tasks],
            self._plan_version(),
        )

    def _create_task(self, args: dict[str, Any]) -> dict[str, Any]:
        data = CreateTaskInput.model_validate(args)
        assignee_id = self._svc.resolve_assignee_id(data.assignee) if data.assignee else None
        task = self._svc.create_task(
            TaskCreate(
                name=data.name,
                description=data.description,
                assignee_id=assignee_id,
                duration=data.duration_days,
                predecessor_ids=data.predecessor_ids,
            )
        )
        return _ok({"task": task.model_dump(mode="json")}, self._plan_version())

    def _update_task(self, args: dict[str, Any]) -> dict[str, Any]:
        data = UpdateTaskInput.model_validate(args)
        task = self._svc.update_task(
            data.task_id,
            TaskUpdate(name=data.name, description=data.description),
        )
        return _ok({"task": task.model_dump(mode="json")}, self._plan_version())

    def _delete_task(self, args: dict[str, Any]) -> dict[str, Any]:
        data = DeleteTaskInput.model_validate(args)
        plan = self._svc.delete_task(data.task_id)
        return _ok({"deleted": data.task_id}, plan.version)

    def _move_task(self, args: dict[str, Any]) -> dict[str, Any]:
        data = MoveTaskInput.model_validate(args)
        task = self._svc.move_task(data.task_id, data.new_start_date)
        return _ok({"task": task.model_dump(mode="json")}, self._plan_version())

    def _set_dependencies(self, args: dict[str, Any]) -> dict[str, Any]:
        data = SetDependenciesInput.model_validate(args)
        task = self._svc.set_dependencies(data.task_id, data.predecessor_ids)
        return _ok({"task": task.model_dump(mode="json")}, self._plan_version())

    def _set_assignee(self, args: dict[str, Any]) -> dict[str, Any]:
        data = SetAssigneeInput.model_validate(args)
        if data.assignee is None or str(data.assignee).strip() == "":
            task = self._svc.update_task(data.task_id, TaskUpdate(clear_assignee=True))
        else:
            assignee_id = self._svc.resolve_assignee_id(data.assignee)
            task = self._svc.update_task(data.task_id, TaskUpdate(assignee_id=assignee_id))
        return _ok({"task": task.model_dump(mode="json")}, self._plan_version())

    def _set_duration(self, args: dict[str, Any]) -> dict[str, Any]:
        data = SetDurationInput.model_validate(args)
        task = self._svc.update_task(
            data.task_id, TaskUpdate(duration=data.duration_days)
        )
        return _ok({"task": task.model_dump(mode="json")}, self._plan_version())

    def _bulk_update_tasks(self, args: dict[str, Any]) -> dict[str, Any]:
        data = BulkUpdateInput.model_validate(args)
        plan = self._svc.bulk_update_tasks(
            data.task_ids,
            assignee=data.changes.assignee,
            duration=data.changes.duration_days,
            description=data.changes.description,
        )
        return _ok(
            {"updated": data.task_ids, "plan_version": plan.version},
            plan.version,
        )
