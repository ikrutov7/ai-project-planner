"""Structured domain errors."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class TaskNotFoundError(DomainError):
    code = "TASK_NOT_FOUND"

    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task not found: {task_id}", details={"task_id": task_id})


class PlanNotFoundError(DomainError):
    code = "PLAN_NOT_FOUND"

    def __init__(self, plan_id: str | None = None) -> None:
        super().__init__(
            "Active plan not found" if plan_id is None else f"Plan not found: {plan_id}",
            details={"plan_id": plan_id},
        )


class AssigneeNotFoundError(DomainError):
    code = "ASSIGNEE_NOT_FOUND"

    def __init__(self, assignee_id: str) -> None:
        super().__init__(
            f"Assignee not found: {assignee_id}",
            details={"assignee_id": assignee_id},
        )


class CircularDependencyError(DomainError):
    code = "CIRCULAR_DEPENDENCY"

    def __init__(self, cycle: list[str]) -> None:
        path = " → ".join(cycle)
        super().__init__(
            f"Dependency cycle detected: {path}",
            details={"cycle": cycle},
        )


class InvalidDependencyError(DomainError):
    code = "INVALID_DEPENDENCY"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, details=details)


class UnknownPredecessorError(DomainError):
    code = "UNKNOWN_PREDECESSOR"

    def __init__(self, predecessor_id: str) -> None:
        super().__init__(
            f"Unknown predecessor: {predecessor_id}",
            details={"predecessor_id": predecessor_id},
        )


class InvalidDurationError(DomainError):
    code = "INVALID_DURATION"

    def __init__(self, duration: int) -> None:
        super().__init__(
            f"duration must be >= 1, got {duration}",
            details={"duration": duration},
        )


class DuplicateTaskNameError(DomainError):
    code = "DUPLICATE_TASK"

    def __init__(self, name: str) -> None:
        super().__init__(f"Task name already exists: {name}", details={"name": name})
