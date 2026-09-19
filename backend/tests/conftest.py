"""Pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("PLANNER_DATABASE_URL", "sqlite:///:memory:")
os.environ.pop("DATABASE_URL", None)

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.repositories import PlanRepository
from app.schemas import AssigneeCreate, PlanCreate, TaskCreate
from app.services import PlanService
import app.db.models  # noqa: F401


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, future=True
    )
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def service(db_session: Session) -> PlanService:
    return PlanService(PlanRepository(db_session))


@pytest.fixture()
def seeded_plan(service: PlanService):
    """Active plan with two assignees."""
    maya = service.create_assignee(AssigneeCreate(name="Maya Chen"))
    alex = service.create_assignee(AssigneeCreate(name="Alex Rivera"))
    plan = service.create_plan(
        PlanCreate(name="Test Plan", project_start=date(2026, 10, 5))
    )
    return plan, maya, alex


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_task(
    service: PlanService,
    *,
    name: str,
    duration: int = 3,
    assignee_id: str | None = None,
    predecessor_ids: list[str] | None = None,
    start_date: date | None = None,
) -> object:
    return service.create_task(
        TaskCreate(
            name=name,
            description=f"Desc for {name}",
            duration=duration,
            assignee_id=assignee_id,
            predecessor_ids=predecessor_ids or [],
            start_date=start_date,
        )
    )
