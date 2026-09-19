"""Engine and session factory."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

_settings = get_settings()
_connect_args: dict = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False
    raw_url = _settings.database_url
    if ":memory:" not in raw_url:
        db_path = raw_url.removeprefix("sqlite:///")
        if db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine: Engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    future=True,
)

if _settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create tables for local scaffold / tests. Prefer Alembic in real deploys."""
    # Import models so metadata is registered.
    import app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
