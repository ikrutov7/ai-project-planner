"""Repository layer — persistence only, no business rules."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import models as orm


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ----- Plan -----

    def get_active_plan(self) -> orm.Plan | None:
        stmt = (
            select(orm.Plan)
            .where(orm.Plan.is_active.is_(True))
            .options(
                selectinload(orm.Plan.tasks).selectinload(orm.Task.dependencies),
                selectinload(orm.Plan.tasks).selectinload(orm.Task.assignee),
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_plan(self, plan_id: str) -> orm.Plan | None:
        stmt = (
            select(orm.Plan)
            .where(orm.Plan.id == plan_id)
            .options(
                selectinload(orm.Plan.tasks).selectinload(orm.Task.dependencies),
                selectinload(orm.Plan.tasks).selectinload(orm.Task.assignee),
            )
        )
        return self._session.scalars(stmt).first()

    def add_plan(self, plan: orm.Plan) -> orm.Plan:
        self._session.add(plan)
        self._session.flush()
        return plan

    def deactivate_all_plans(self) -> None:
        for plan in self._session.scalars(select(orm.Plan).where(orm.Plan.is_active.is_(True))):
            plan.is_active = False
            plan.updated_at = _utc_now()

    def bump_plan_version(self, plan: orm.Plan) -> None:
        plan.version += 1
        plan.updated_at = _utc_now()
        self._session.flush()

    def delete_plan(self, plan: orm.Plan) -> None:
        self._session.delete(plan)
        self._session.flush()

    # ----- Assignee -----

    def list_assignees(self) -> list[orm.Assignee]:
        return list(self._session.scalars(select(orm.Assignee).order_by(orm.Assignee.name)))

    def get_assignee(self, assignee_id: str) -> orm.Assignee | None:
        return self._session.get(orm.Assignee, assignee_id)

    def get_assignee_by_name(self, name: str) -> orm.Assignee | None:
        stmt = select(orm.Assignee).where(orm.Assignee.name == name)
        return self._session.scalars(stmt).first()

    def add_assignee(self, assignee: orm.Assignee) -> orm.Assignee:
        self._session.add(assignee)
        self._session.flush()
        return assignee

    # ----- Task -----

    def get_task(self, task_id: str) -> orm.Task | None:
        stmt = (
            select(orm.Task)
            .where(orm.Task.id == task_id)
            .options(selectinload(orm.Task.dependencies))
        )
        return self._session.scalars(stmt).first()

    def list_tasks(self, plan_id: str) -> list[orm.Task]:
        stmt = (
            select(orm.Task)
            .where(orm.Task.plan_id == plan_id)
            .options(selectinload(orm.Task.dependencies))
            .order_by(orm.Task.start_date, orm.Task.name)
        )
        return list(self._session.scalars(stmt))

    def find_task_by_name(self, plan_id: str, name: str) -> orm.Task | None:
        stmt = select(orm.Task).where(orm.Task.plan_id == plan_id, orm.Task.name == name)
        return self._session.scalars(stmt).first()

    def add_task(self, task: orm.Task) -> orm.Task:
        self._session.add(task)
        self._session.flush()
        return task

    def delete_task(self, task: orm.Task) -> None:
        self._session.delete(task)
        self._session.flush()

    # ----- Dependency -----

    def list_dependencies_for_plan(self, plan_id: str) -> list[orm.Dependency]:
        stmt = (
            select(orm.Dependency)
            .join(orm.Task, orm.Dependency.task_id == orm.Task.id)
            .where(orm.Task.plan_id == plan_id)
        )
        return list(self._session.scalars(stmt))

    def set_task_dependencies(
        self, task: orm.Task, predecessor_ids: list[str]
    ) -> list[orm.Dependency]:
        task.dependencies.clear()
        self._session.flush()
        created: list[orm.Dependency] = []
        for pred_id in predecessor_ids:
            dep = orm.Dependency(predecessor_id=pred_id)
            task.dependencies.append(dep)
            created.append(dep)
        self._session.flush()
        self._session.refresh(task)
        return created

    def delete_dependencies_referencing(self, task_id: str) -> None:
        """Remove edges where task is predecessor or successor."""
        deps = list(
            self._session.scalars(
                select(orm.Dependency).where(
                    (orm.Dependency.task_id == task_id)
                    | (orm.Dependency.predecessor_id == task_id)
                )
            )
        )
        for dep in deps:
            self._session.delete(dep)
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    def flush(self) -> None:
        self._session.flush()
