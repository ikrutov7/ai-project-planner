"""Excel and MCP integration tests."""

from __future__ import annotations

from datetime import date

from app.excel.service import export_xlsx, import_xlsx
from app.mcp.tools import MCPServer
from app.schemas import TaskCreate
from app.seed import seed_demo_plan
from tests.conftest import make_task


def test_excel_roundtrip(service, db_session):
    seed_demo_plan(db_session, force=True)
    plan = service.get_active_plan()
    blob = export_xlsx(plan)
    parsed = import_xlsx(blob, project_start=plan.project_start)
    assert len(parsed["rows"]) == len(plan.tasks)
    names = {r["name"] for r in parsed["rows"]}
    assert "Product Discovery" in names


def test_excel_import_replaces_plan(service, db_session):
    seed_demo_plan(db_session, force=True)
    rows = [
        {
            "name": "A",
            "description": "first",
            "assignee": "Maya Chen",
            "duration": 2,
            "predecessors": [],
        },
        {
            "name": "B",
            "description": "second",
            "assignee": "Alex Rivera",
            "duration": 3,
            "predecessors": ["A"],
        },
    ]
    plan = service.replace_plan_from_rows(
        name="Imported",
        project_start=date(2026, 10, 5),
        rows=rows,
    )
    assert len(plan.tasks) == 2
    b = next(t for t in plan.tasks if t.name == "B")
    assert len(b.predecessor_ids) == 1


def test_mcp_move_and_bulk(service, seeded_plan):
    plan, maya, _alex = seeded_plan
    t1 = make_task(service, name="Alpha", duration=2, assignee_id=maya.id)
    t2 = make_task(service, name="Beta", duration=2, assignee_id=maya.id, predecessor_ids=[t1.id])
    mcp = MCPServer(service)
    moved = mcp.call_tool(
        "move_task",
        {"task_id": t2.id, "new_start_date": "2026-11-01"},
    )
    assert moved["success"] is True
    bulk = mcp.call_tool(
        "bulk_update_tasks",
        {"task_ids": [t1.id, t2.id], "changes": {"assignee": "Sofia Berg"}},
    )
    assert bulk["success"] is True
    search = mcp.call_tool("search_tasks", {"query": "alpha"})
    assert search["success"] is True
    assert len(search["data"]) >= 1


def test_chat_demo_agent(client, db_session):
    seed_demo_plan(db_session, force=True)
    db_session.commit()
    resp = client.post("/api/chat", json={"message": "Перенеси UX Wireframes на 7 дней позже"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "demo"
    assert "plan" in body
    assert body["plan"]["version"] >= 1


def test_chat_demo_create_task_parses_name_and_duration(client, db_session):
    seed_demo_plan(db_session, force=True)
    db_session.commit()
    resp = client.post("/api/chat", json={"message": "Создай задачу QA Pass на 2 дня"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "demo"
    names = {t["name"] for t in body["plan"]["tasks"]}
    assert "QA Pass" in names
    created = next(t for t in body["plan"]["tasks"] if t["name"] == "QA Pass")
    assert created["duration"] == 2
    assert "QA Pass" in body["message"]["content"]


def test_plan_endpoint(client, db_session):
    seed_demo_plan(db_session, force=True)
    db_session.commit()
    resp = client.get("/api/plan")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tasks"]) == 20
