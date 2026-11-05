"""Synchronous SQLAlchemy engine and session helpers.

The FastAPI app is sync today (health routes and TestClient). F1.2 keeps
the same sync session style so existing endpoints do not change behaviour.
"""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set a PostgreSQL URL before using the database."
        )
    if settings.database_url.startswith("sqlite"):
        raise RuntimeError(
            "SQLite is not supported for the production schema. Use PostgreSQL."
        )
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for scripts, migrations helpers, and tests."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> bool:
    """Return True when PostgreSQL accepts a simple SELECT 1."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def reset_engine_cache() -> None:
    """Clear cached engine/session factory. Used by tests that change DATABASE_URL."""
    get_session_factory.cache_clear()
    get_engine.cache_clear()
