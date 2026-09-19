"""SQLAlchemy ORM models: Plan, Assignee, Task, Dependency."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import TaskStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Assignee(Base):
    __tablename__ = "assignees"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    tasks: Mapped[list[Task]] = relationship(back_populates="assignee")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_start: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    tasks: Mapped[list[Task]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assignee_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("assignees.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TaskStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    plan: Mapped[Plan] = relationship(back_populates="tasks")
    assignee: Mapped[Assignee | None] = relationship(back_populates="tasks")
    dependencies: Mapped[list[Dependency]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        foreign_keys="Dependency.task_id",
    )


class Dependency(Base):
    """Finish-to-Start edge: predecessor must finish before task starts."""

    __tablename__ = "dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "predecessor_id", name="uq_dependency_edge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    predecessor_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    task: Mapped[Task] = relationship(
        back_populates="dependencies",
        foreign_keys=[task_id],
    )
