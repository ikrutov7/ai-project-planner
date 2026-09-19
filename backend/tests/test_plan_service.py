"""PlanService unit tests: tasks, dependencies, dates, cycles."""

from datetime import date

import pytest

from app.domain.enums import TaskStatus
from app.domain.errors import CircularDependencyError, TaskNotFoundError
from app.schemas import TaskUpdate
from tests.conftest import make_task


def test_create_task_computes_end_date(service, seeded_plan):
    plan, maya, _alex = seeded_plan
    task = make_task(
        service,
        name="Discovery",
        duration=3,
        assignee_id=maya.id,
        start_date=plan.project_start,
    )
    assert task.start_date == date(2026, 10, 5)
    assert task.duration == 3
    assert task.end_date == date(2026, 10, 7)
    assert task.assignee_id == maya.id
    assert task.status == TaskStatus.PENDING
    assert task.plan_id == plan.id


def test_update_task_recalculates_end_date(service, seeded_plan):
    _plan, maya, _alex = seeded_plan
    task = make_task(service, name="Wireframes", duration=2, assignee_id=maya.id)
    updated = service.update_task(
        task.id,
        TaskUpdate(duration=5, description="Updated desc"),
    )
    assert updated.duration == 5
    assert updated.end_date == compute_expected_end(updated.start_date, 5)
    assert updated.description == "Updated desc"


def compute_expected_end(start: date, duration: int) -> date:
    from app.domain.scheduling import compute_end_date

    return compute_end_date(start, duration)


def test_update_task_change_assignee(service, seeded_plan):
    _plan, maya, alex = seeded_plan
    task = make_task(service, name="API", duration=2, assignee_id=maya.id)
    updated = service.update_task(task.id, TaskUpdate(assignee_id=alex.id))
    assert updated.assignee_id == alex.id


def test_dependencies_shift_successor_start(service, seeded_plan):
    _plan, maya, alex = seeded_plan
    a = make_task(service, name="A", duration=3, assignee_id=maya.id)
    b = make_task(
        service,
        name="B",
        duration=2,
        assignee_id=alex.id,
        predecessor_ids=[a.id],
    )
    assert a.end_date == date(2026, 10, 7)
    assert b.start_date == date(2026, 10, 8)
    assert b.end_date == date(2026, 10, 9)
    assert b.predecessor_ids == [a.id]


def test_set_dependencies_diamond(service, seeded_plan):
    _plan, maya, alex = seeded_plan
    a = make_task(service, name="A", duration=2, assignee_id=maya.id)
    b = make_task(service, name="B", duration=2, assignee_id=alex.id)
    c = make_task(service, name="C", duration=1, assignee_id=maya.id)
    c = service.set_dependencies(c.id, [a.id, b.id])
    assert set(c.predecessor_ids) == {a.id, b.id}
    expected_start = max(a.end_date, b.end_date)
    from datetime import timedelta

    assert c.start_date == expected_start + timedelta(days=1)


def test_circular_dependency_rejected(service, seeded_plan):
    _plan, maya, _alex = seeded_plan
    a = make_task(service, name="A", duration=1, assignee_id=maya.id)
    b = make_task(
        service,
        name="B",
        duration=1,
        assignee_id=maya.id,
        predecessor_ids=[a.id],
    )
    with pytest.raises(CircularDependencyError):
        service.set_dependencies(a.id, [b.id])


def test_self_dependency_rejected(service, seeded_plan):
    _plan, maya, _alex = seeded_plan
    a = make_task(service, name="A", duration=1, assignee_id=maya.id)
    from app.domain.errors import InvalidDependencyError

    with pytest.raises(InvalidDependencyError):
        service.set_dependencies(a.id, [a.id])


def test_long_cycle_rejected(service, seeded_plan):
    _plan, maya, _alex = seeded_plan
    a = make_task(service, name="A", duration=1, assignee_id=maya.id)
    b = make_task(
        service, name="B", duration=1, assignee_id=maya.id, predecessor_ids=[a.id]
    )
    c = make_task(
        service, name="C", duration=1, assignee_id=maya.id, predecessor_ids=[b.id]
    )
    with pytest.raises(CircularDependencyError):
        service.set_dependencies(a.id, [c.id])


def test_get_missing_task(service, seeded_plan):
    with pytest.raises(TaskNotFoundError):
        service.get_task("task-missing")


def test_duration_change_propagates_to_successor(service, seeded_plan):
    _plan, maya, alex = seeded_plan
    a = make_task(service, name="A", duration=2, assignee_id=maya.id)
    b = make_task(
        service, name="B", duration=1, assignee_id=alex.id, predecessor_ids=[a.id]
    )
    assert b.start_date == date(2026, 10, 7)
    service.update_task(a.id, TaskUpdate(duration=5))
    b2 = service.get_task(b.id)
    assert b2.start_date == date(2026, 10, 10)
