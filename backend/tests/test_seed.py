"""Seed data tests."""

from app.seed import TASK_SPECS, build_seed_plan, seed_demo_plan


def test_build_seed_plan_has_twenty_tasks():
    plan = build_seed_plan()
    assert len(plan.tasks) == 20
    assert len(TASK_SPECS) == 20


def test_seed_plan_dates_consistent():
    plan = build_seed_plan()
    by_id = {t.id: t for t in plan.tasks}
    for task in plan.tasks:
        assert task.end_date >= task.start_date
        expected_days = (task.end_date - task.start_date).days + 1
        assert expected_days == task.duration
        for dep in task.dependencies:
            pred = by_id[dep.predecessor_id]
            assert task.start_date > pred.end_date


def test_seed_demo_plan_persists(db_session):
    plan = seed_demo_plan(db_session, force=True)
    assert plan.id == "plan-demo"
    assert len(plan.tasks) == 20
    assignees = {t.assignee_id for t in plan.tasks}
    assert len(assignees) >= 4
