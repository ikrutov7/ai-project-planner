"""Health endpoint smoke tests."""


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


def test_domain_models_importable():
    from app.db.models import Assignee, Dependency, Plan, Task

    assert Plan.__tablename__ == "plans"
    assert Task.__tablename__ == "tasks"
    assert Assignee.__tablename__ == "assignees"
    assert Dependency.__tablename__ == "dependencies"
