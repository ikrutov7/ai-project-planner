"""Demo seed: realistic ~20-task project with assignees and dependencies."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.db import models as orm
from app.domain.enums import TaskStatus
from app.domain.scheduling import compute_end_date, earliest_start_after_predecessors, topological_order
from app.repositories import PlanRepository
from app.services.plan_service import PlanService


ASSIGNEE_SPECS = [
    ("assignee-maya", "Maya Chen"),
    ("assignee-alex", "Alex Rivera"),
    ("assignee-sofia", "Sofia Berg"),
    ("assignee-jordan", "Jordan Lee"),
    ("assignee-sam", "Sam Okonkwo"),
]

# (id, name, description, assignee_id, duration, predecessor_ids)
TASK_SPECS: list[tuple[str, str, str, str, int, list[str]]] = [
    (
        "task-01",
        "Product Discovery",
        "Clarify MVP scope, personas, and success metrics.",
        "assignee-maya",
        3,
        [],
    ),
    (
        "task-02",
        "UX Wireframes",
        "Low-fidelity flows for planner, Gantt, and chat.",
        "assignee-maya",
        4,
        ["task-01"],
    ),
    (
        "task-03",
        "UI Design System",
        "Visual language for Gantt bars, chat, and modals.",
        "assignee-sofia",
        5,
        ["task-02"],
    ),
    (
        "task-04",
        "Architecture Spike",
        "Domain model, MCP boundary, scheduling approach.",
        "assignee-alex",
        3,
        ["task-01"],
    ),
    (
        "task-05",
        "API Contract",
        "REST endpoints and Plan/Task DTO schema.",
        "assignee-alex",
        2,
        ["task-04"],
    ),
    (
        "task-06",
        "Domain Model & PlanService",
        "Canonical mutations, validation, draft transactions.",
        "assignee-alex",
        4,
        ["task-05"],
    ),
    (
        "task-07",
        "Scheduler Engine",
        "Deterministic FS scheduling and cycle detection.",
        "assignee-jordan",
        3,
        ["task-06"],
    ),
    (
        "task-08",
        "Backend API",
        "FastAPI routes for plan, tasks, import/export, chat.",
        "assignee-jordan",
        5,
        ["task-07"],
    ),
    (
        "task-09",
        "Excel Import/Export",
        "Parse and write xlsx compatible with planner columns.",
        "assignee-jordan",
        3,
        ["task-08"],
    ),
    (
        "task-10",
        "MCP Tool Layer",
        "Typed MCP tools wrapping PlanService mutations.",
        "assignee-alex",
        4,
        ["task-06"],
    ),
    (
        "task-11",
        "LLM Agent Loop",
        "Chat turn orchestration with tool calling.",
        "assignee-alex",
        4,
        ["task-10", "task-08"],
    ),
    (
        "task-12",
        "Frontend Scaffold",
        "Vite React TypeScript app shell and routing.",
        "assignee-sofia",
        3,
        ["task-03"],
    ),
    (
        "task-13",
        "Gantt Chart UI",
        "Interactive Gantt bound to plan state.",
        "assignee-sofia",
        5,
        ["task-12", "task-08"],
    ),
    (
        "task-14",
        "Task Detail Modal",
        "View and edit task fields from Gantt click.",
        "assignee-sofia",
        2,
        ["task-13"],
    ),
    (
        "task-15",
        "AI Chat Panel",
        "Right-rail chat UI wired to /api/chat.",
        "assignee-maya",
        4,
        ["task-12", "task-11"],
    ),
    (
        "task-16",
        "Excel UI Actions",
        "Import/export buttons and error toasts.",
        "assignee-maya",
        2,
        ["task-09", "task-12"],
    ),
    (
        "task-17",
        "Integration Tests",
        "API, scheduler, MCP, and Excel roundtrip tests.",
        "assignee-sam",
        4,
        ["task-08", "task-09", "task-10"],
    ),
    (
        "task-18",
        "E2E Smoke Demo",
        "Seed → import → chat mutation → export path.",
        "assignee-sam",
        3,
        ["task-13", "task-15", "task-16", "task-17"],
    ),
    (
        "task-19",
        "Deployment Packaging",
        "Dockerfile, compose, env samples, README runbook.",
        "assignee-jordan",
        2,
        ["task-18"],
    ),
    (
        "task-20",
        "Demo Rehearsal",
        "Walkthrough script and polish for assignment review.",
        "assignee-maya",
        2,
        ["task-19"],
    ),
]


def build_seed_plan(*, project_start: date | None = None) -> orm.Plan:
    """Build an in-memory ORM graph (not yet persisted)."""
    start = project_start or date(2026, 10, 5)
    plan = orm.Plan(
        id="plan-demo",
        name="AI Project Planner MVP",
        project_start=start,
        version=1,
        is_active=True,
    )

    assignees = {
        aid: orm.Assignee(id=aid, name=name) for aid, name in ASSIGNEE_SPECS
    }

    # First pass: tasks without dates; second: schedule.
    tasks: dict[str, orm.Task] = {}
    edges: dict[str, list[str]] = {}
    for tid, name, desc, assignee_id, duration, preds in TASK_SPECS:
        tasks[tid] = orm.Task(
            id=tid,
            plan_id=plan.id,
            name=name,
            description=desc,
            assignee_id=assignee_id,
            start_date=start,
            duration=duration,
            end_date=compute_end_date(start, duration),
            status=TaskStatus.PENDING.value,
        )
        edges[tid] = list(preds)

    order = topological_order(tasks.keys(), edges)
    for tid in order:
        task = tasks[tid]
        pred_ends = [tasks[p].end_date for p in edges[tid]]
        task.start_date = earliest_start_after_predecessors(
            pred_ends, project_start=start
        )
        task.end_date = compute_end_date(task.start_date, task.duration)

    plan.tasks = list(tasks.values())
    # Attach dependency objects
    for tid, preds in edges.items():
        tasks[tid].dependencies = [
            orm.Dependency(task_id=tid, predecessor_id=p) for p in preds
        ]

    # Return plan + assignees separately via attribute for seeder
    plan._seed_assignees = list(assignees.values())  # type: ignore[attr-defined]
    return plan


def seed_demo_plan(session: Session, *, force: bool = False) -> orm.Plan:
    """Persist demo plan. If an active plan exists and force is False, return it."""
    repo = PlanRepository(session)
    existing = repo.get_active_plan()
    if existing is not None and not force:
        return existing

    if force and existing is not None:
        repo.delete_plan(existing)
        session.flush()

    # Clear previous demo assignees if re-seeding (keep other assignees)
    plan = build_seed_plan()
    assignees: list[orm.Assignee] = getattr(plan, "_seed_assignees")

    for assignee in assignees:
        if repo.get_assignee(assignee.id) is None:
            repo.add_assignee(assignee)

    repo.deactivate_all_plans()
    # Detach helper attr before add
    if hasattr(plan, "_seed_assignees"):
        delattr(plan, "_seed_assignees")
    repo.add_plan(plan)
    session.commit()
    loaded = repo.get_plan(plan.id)
    assert loaded is not None
    return loaded


def seed_if_empty(session: Session) -> None:
    repo = PlanRepository(session)
    if repo.get_active_plan() is None:
        seed_demo_plan(session, force=False)


def main() -> None:
    from app.db.session import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        plan = seed_demo_plan(session, force=True)
        service = PlanService(PlanRepository(session))
        read = service.get_active_plan()
        print(f"Seeded plan {plan.id!r}: {len(read.tasks)} tasks, {len(read.assignees)} assignees")
        for task in read.tasks:
            preds = ",".join(task.predecessor_ids) or "-"
            print(
                f"  {task.id}: {task.name} [{task.start_date}→{task.end_date}] "
                f"dur={task.duration} preds={preds} assignee={task.assignee_id}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
