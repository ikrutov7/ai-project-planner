"""PlanService — single mutation gateway; owns business rules."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.db import models as orm
from app.domain.enums import TaskStatus
from app.domain.errors import (
    AssigneeNotFoundError,
    CircularDependencyError,
    DuplicateTaskNameError,
    InvalidDependencyError,
    InvalidDurationError,
    PlanNotFoundError,
    TaskNotFoundError,
    UnknownPredecessorError,
)
from app.domain.scheduling import (
    compute_end_date,
    earliest_start_after_predecessors,
    topological_order,
    would_create_cycle,
)
from app.repositories import PlanRepository
from app.schemas import (
    AssigneeCreate,
    AssigneeRead,
    PlanCreate,
    PlanRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


class PlanService:
    def __init__(self, repo: PlanRepository) -> None:
        self._repo = repo

    # ----- reads -----

    def get_active_plan(self) -> PlanRead:
        plan = self._repo.get_active_plan()
        if plan is None:
            raise PlanNotFoundError()
        return self._to_plan_read(plan)

    def get_task(self, task_id: str) -> TaskRead:
        task = self._require_task(task_id)
        return self._to_task_read(task)

    # ----- assignees -----

    def create_assignee(self, data: AssigneeCreate) -> AssigneeRead:
        existing = self._repo.get_assignee_by_name(data.name.strip())
        if existing is not None:
            return AssigneeRead.model_validate(existing)
        assignee = orm.Assignee(id=new_id("assignee"), name=data.name.strip())
        self._repo.add_assignee(assignee)
        return AssigneeRead.model_validate(assignee)

    # ----- plans -----

    def create_plan(self, data: PlanCreate, *, activate: bool = True) -> PlanRead:
        if activate:
            self._repo.deactivate_all_plans()
        plan = orm.Plan(
            id=new_id("plan"),
            name=data.name.strip(),
            project_start=data.project_start,
            version=1,
            is_active=activate,
        )
        self._repo.add_plan(plan)
        return self._to_plan_read(plan)

    def replace_with_seed_plan(self, plan: orm.Plan) -> PlanRead:
        """Persist a fully built ORM plan graph (used by seed)."""
        self._repo.deactivate_all_plans()
        plan.is_active = True
        self._repo.add_plan(plan)
        self._repo.flush()
        loaded = self._repo.get_plan(plan.id)
        assert loaded is not None
        return self._to_plan_read(loaded)

    # ----- tasks -----

    def create_task(self, data: TaskCreate, *, plan_id: str | None = None) -> TaskRead:
        plan = self._resolve_plan(plan_id)
        name = data.name.strip()
        if not name:
            raise InvalidDependencyError("Task name must not be blank")
        if self._repo.find_task_by_name(plan.id, name) is not None:
            raise DuplicateTaskNameError(name)
        if data.duration < 1:
            raise InvalidDurationError(data.duration)
        if data.assignee_id is not None:
            self._require_assignee(data.assignee_id)

        predecessor_ids = self._normalize_preds(data.predecessor_ids)
        self._assert_predecessors_exist(plan.id, predecessor_ids)

        task_id = new_id("task")
        edges = self._dependency_edges(plan.id)
        edges[task_id] = []
        cycle = would_create_cycle(
            task_id=task_id,
            predecessor_ids=predecessor_ids,
            edges=edges,
        )
        if cycle:
            raise CircularDependencyError(cycle)

        start = data.start_date or self._compute_start(plan, predecessor_ids)
        end = compute_end_date(start, data.duration)

        task = orm.Task(
            id=task_id,
            plan_id=plan.id,
            name=name,
            description=data.description,
            assignee_id=data.assignee_id,
            start_date=start,
            duration=data.duration,
            end_date=end,
            status=data.status.value if isinstance(data.status, TaskStatus) else str(data.status),
        )
        self._repo.add_task(task)
        if predecessor_ids:
            self._repo.set_task_dependencies(task, predecessor_ids)

        self._reschedule_plan(plan.id)
        self._repo.bump_plan_version(plan)
        return self._to_task_read(self._require_task(task_id))

    def update_task(self, task_id: str, data: TaskUpdate) -> TaskRead:
        task = self._require_task(task_id)
        plan = self._require_plan(task.plan_id)

        if data.name is not None:
            name = data.name.strip()
            other = self._repo.find_task_by_name(plan.id, name)
            if other is not None and other.id != task.id:
                raise DuplicateTaskNameError(name)
            task.name = name

        if data.description is not None:
            task.description = data.description

        if data.clear_assignee:
            task.assignee_id = None
        elif data.assignee_id is not None:
            self._require_assignee(data.assignee_id)
            task.assignee_id = data.assignee_id

        if data.status is not None:
            task.status = data.status.value

        duration = data.duration if data.duration is not None else task.duration
        if duration < 1:
            raise InvalidDurationError(duration)

        start = data.start_date if data.start_date is not None else task.start_date
        task.duration = duration
        task.start_date = start
        task.end_date = compute_end_date(start, duration)

        self._repo.flush()
        self._reschedule_plan(plan.id)
        self._repo.bump_plan_version(plan)
        return self._to_task_read(self._require_task(task_id))

    def set_dependencies(self, task_id: str, predecessor_ids: list[str]) -> TaskRead:
        task = self._require_task(task_id)
        plan = self._require_plan(task.plan_id)
        preds = self._normalize_preds(predecessor_ids)

        if task_id in preds:
            raise InvalidDependencyError(
                "Task cannot depend on itself",
                task_id=task_id,
            )

        self._assert_predecessors_exist(plan.id, preds)
        edges = self._dependency_edges(plan.id)
        edges_without = {tid: (ps if tid != task_id else []) for tid, ps in edges.items()}
        cycle = would_create_cycle(
            task_id=task_id,
            predecessor_ids=preds,
            edges=edges_without,
        )
        if cycle:
            raise CircularDependencyError(cycle)

        self._repo.set_task_dependencies(task, preds)
        self._reschedule_plan(plan.id)
        self._repo.bump_plan_version(plan)
        return self._to_task_read(self._require_task(task_id))

    def delete_task(self, task_id: str) -> PlanRead:
        task = self._require_task(task_id)
        plan_id = task.plan_id
        self._repo.delete_dependencies_referencing(task_id)
        self._repo.delete_task(task)
        self._reschedule_plan(plan_id)
        plan = self._require_plan(plan_id)
        self._repo.bump_plan_version(plan)
        return self._to_plan_read(plan)

    def move_task(self, task_id: str, new_start_date: date) -> TaskRead:
        return self.update_task(task_id, TaskUpdate(start_date=new_start_date))

    def search_tasks(self, query: str) -> list[TaskRead]:
        plan = self.get_active_plan()
        q = query.strip().lower()
        if not q:
            return list(plan.tasks)
        assignee_names = {a.id: a.name.lower() for a in plan.assignees}
        hits: list[TaskRead] = []
        for task in plan.tasks:
            hay = " ".join(
                [
                    task.id.lower(),
                    task.name.lower(),
                    task.description.lower(),
                    assignee_names.get(task.assignee_id or "", ""),
                ]
            )
            if q in hay:
                hits.append(task)
        return hits

    def resolve_assignee_id(self, assignee: str | None) -> str | None:
        """Resolve assignee by id or display name; create if name unknown."""
        if assignee is None:
            return None
        value = assignee.strip()
        if not value:
            return None
        by_id = self._repo.get_assignee(value)
        if by_id is not None:
            return by_id.id
        by_name = self._repo.get_assignee_by_name(value)
        if by_name is not None:
            return by_name.id
        # fuzzy: case-insensitive / partial
        for existing in self._repo.list_assignees():
            if existing.name.lower() == value.lower() or value.lower() in existing.name.lower():
                return existing.id
        created = self.create_assignee(AssigneeCreate(name=value))
        return created.id

    def bulk_update_tasks(
        self,
        task_ids: list[str],
        *,
        assignee: str | None = None,
        clear_assignee: bool = False,
        duration: int | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
    ) -> PlanRead:
        if not task_ids:
            raise InvalidDependencyError("task_ids must not be empty")
        assignee_id: str | None = None
        if clear_assignee:
            assignee_id = None
        elif assignee is not None:
            assignee_id = self.resolve_assignee_id(assignee)

        for tid in task_ids:
            self._require_task(tid)

        for tid in task_ids:
            payload: dict = {}
            if description is not None:
                payload["description"] = description
            if duration is not None:
                payload["duration"] = duration
            if status is not None:
                payload["status"] = status
            if clear_assignee:
                payload["clear_assignee"] = True
            elif assignee is not None:
                payload["assignee_id"] = assignee_id
            self.update_task(tid, TaskUpdate(**payload))
        return self.get_active_plan()
    def replace_plan_from_rows(
        self,
        *,
        name: str,
        project_start: date,
        rows: list[dict],
    ) -> PlanRead:
        """
        Replace active plan from Excel-like rows.
        Each row: name, description, assignee (str|None), duration (int), predecessors (list[str] names).
        """
        if not rows:
            raise InvalidDependencyError("Import contains no tasks")

        names = [str(r["name"]).strip() for r in rows]
        if len(names) != len(set(names)):
            raise DuplicateTaskNameError("duplicate task names in import")

        name_to_temp: dict[str, str] = {n: new_id("task") for n in names}

        # Resolve predecessors by name before creating anything
        for row in rows:
            for pred_name in row.get("predecessors") or []:
                if pred_name not in name_to_temp:
                    raise UnknownPredecessorError(pred_name)

        # Cycle check on name graph
        edges_by_id = {
            name_to_temp[str(r["name"]).strip()]: [
                name_to_temp[p] for p in (r.get("predecessors") or [])
            ]
            for r in rows
        }
        try:
            topological_order(edges_by_id.keys(), edges_by_id)
        except ValueError as exc:
            raise CircularDependencyError(["import-cycle"]) from exc

        existing = self._repo.get_active_plan()
        if existing is not None:
            self._repo.delete_plan(existing)
            self._repo.flush()

        plan = orm.Plan(
            id=new_id("plan"),
            name=name.strip() or "Imported Plan",
            project_start=project_start,
            version=1,
            is_active=True,
        )
        self._repo.deactivate_all_plans()
        self._repo.add_plan(plan)

        for row in rows:
            tname = str(row["name"]).strip()
            duration = int(row["duration"])
            if duration < 1:
                raise InvalidDurationError(duration)
            assignee_raw = row.get("assignee")
            assignee_id = self.resolve_assignee_id(assignee_raw) if assignee_raw else None
            task = orm.Task(
                id=name_to_temp[tname],
                plan_id=plan.id,
                name=tname,
                description=str(row.get("description") or ""),
                assignee_id=assignee_id,
                start_date=project_start,
                duration=duration,
                end_date=compute_end_date(project_start, duration),
                status=TaskStatus.PENDING.value,
            )
            self._repo.add_task(task)

        for row in rows:
            tname = str(row["name"]).strip()
            tid = name_to_temp[tname]
            preds = [name_to_temp[p] for p in (row.get("predecessors") or [])]
            if preds:
                task = self._require_task(tid)
                self._repo.set_task_dependencies(task, preds)

        self._reschedule_plan(plan.id)
        self._repo.flush()
        loaded = self._repo.get_plan(plan.id)
        assert loaded is not None
        return self._to_plan_read(loaded)

    def reset_to_seed(self) -> PlanRead:
        from app.seed import seed_demo_plan

        seed_demo_plan(self._repo._session, force=True)
        return self.get_active_plan()

    # ----- internals -----

    def _resolve_plan(self, plan_id: str | None) -> orm.Plan:
        if plan_id is None:
            plan = self._repo.get_active_plan()
            if plan is None:
                raise PlanNotFoundError()
            return plan
        return self._require_plan(plan_id)

    def _require_plan(self, plan_id: str) -> orm.Plan:
        plan = self._repo.get_plan(plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)
        return plan

    def _require_task(self, task_id: str) -> orm.Task:
        task = self._repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def _require_assignee(self, assignee_id: str) -> orm.Assignee:
        assignee = self._repo.get_assignee(assignee_id)
        if assignee is None:
            raise AssigneeNotFoundError(assignee_id)
        return assignee

    @staticmethod
    def _normalize_preds(predecessor_ids: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for pid in predecessor_ids:
            if pid not in seen:
                seen.add(pid)
                ordered.append(pid)
        return ordered

    def _assert_predecessors_exist(self, plan_id: str, predecessor_ids: list[str]) -> None:
        tasks = {t.id: t for t in self._repo.list_tasks(plan_id)}
        for pid in predecessor_ids:
            if pid not in tasks:
                raise UnknownPredecessorError(pid)

    def _dependency_edges(self, plan_id: str) -> dict[str, list[str]]:
        tasks = self._repo.list_tasks(plan_id)
        edges: dict[str, list[str]] = {t.id: [] for t in tasks}
        for dep in self._repo.list_dependencies_for_plan(plan_id):
            edges.setdefault(dep.task_id, []).append(dep.predecessor_id)
        return edges

    def _compute_start(self, plan: orm.Plan, predecessor_ids: list[str]) -> date:
        if not predecessor_ids:
            return plan.project_start
        ends = [self._require_task(pid).end_date for pid in predecessor_ids]
        return earliest_start_after_predecessors(ends, project_start=plan.project_start)

    def _reschedule_plan(self, plan_id: str) -> None:
        """Recompute starts/ends in topo order (FS). Soft pin: max(earliest_FS, start)."""
        plan = self._require_plan(plan_id)
        tasks = {t.id: t for t in self._repo.list_tasks(plan_id)}
        edges = self._dependency_edges(plan_id)
        try:
            order = topological_order(tasks.keys(), edges)
        except ValueError as exc:
            raise CircularDependencyError(["<cycle>"]) from exc

        for tid in order:
            task = tasks[tid]
            pred_ends = [tasks[p].end_date for p in edges.get(tid, [])]
            earliest = earliest_start_after_predecessors(
                pred_ends, project_start=plan.project_start
            )
            start = max(earliest, task.start_date)
            task.start_date = start
            task.end_date = compute_end_date(start, task.duration)
        self._repo.flush()

    def _to_task_read(self, task: orm.Task) -> TaskRead:
        pred_ids = [d.predecessor_id for d in task.dependencies]
        return TaskRead(
            id=task.id,
            plan_id=task.plan_id,
            name=task.name,
            description=task.description,
            assignee_id=task.assignee_id,
            start_date=task.start_date,
            duration=task.duration,
            end_date=task.end_date,
            status=TaskStatus(task.status),
            created_at=task.created_at,
            updated_at=task.updated_at,
            predecessor_ids=pred_ids,
        )

    def _to_plan_read(self, plan: orm.Plan) -> PlanRead:
        tasks = [self._to_task_read(t) for t in plan.tasks]
        tasks.sort(key=lambda t: (t.start_date, t.name))
        assignees = [AssigneeRead.model_validate(a) for a in self._repo.list_assignees()]
        return PlanRead(
            id=plan.id,
            name=plan.name,
            project_start=plan.project_start,
            version=plan.version,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            tasks=tasks,
            assignees=assignees,
        )
