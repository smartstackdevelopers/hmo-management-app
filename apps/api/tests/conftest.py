"""Pytest fixtures for PostgreSQL-backed schema tests.

Database tests require TEST_DATABASE_URL or DATABASE_URL pointing at PostgreSQL.
They are skipped when no URL is configured so F1.1 health tests still run offline.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "postgres: requires a live PostgreSQL database with pgvector",
    )
    config.addinivalue_line(
        "markers",
        "no_ai_feature_flag_auto_enable: skip F3.15 auto-enable of AI features for this test",
    )


def _database_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = _database_url()
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL or DATABASE_URL is not set. "
            "PostgreSQL schema tests were not executed."
        )
    if url.startswith("sqlite"):
        pytest.fail("SQLite cannot be used to claim PostgreSQL compatibility.")
    return url


@pytest.fixture(scope="session")
def alembic_config(postgres_url: str) -> Config:
    os.environ["DATABASE_URL"] = postgres_url
    get_settings.cache_clear()
    config = Config("alembic.ini")
    return config


@pytest.fixture(scope="session")
def migrated_engine(alembic_config: Config, postgres_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(postgres_url, future=True, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        connection.commit()

    command.upgrade(alembic_config, "head")
    yield engine

    command.downgrade(alembic_config, "base")
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture()
def db_session(migrated_engine: Engine) -> Generator[Session, None, None]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autoflush=False, future=True)
    session = SessionLocal()
    # Tests seed fixtures under an explicit platform RLS bypass; isolation tests
    # switch to organisation-scoped SET LOCAL when asserting tenant boundaries.
    from app.tenancy.session_rls import apply_platform_rls_bypass

    apply_platform_rls_bypass(session)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture(autouse=True)
def auto_enable_ai_feature_flags(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Preserve pre-F3.15 AI availability for existing Phase 3 tests.

    Production remains fail-closed for missing config. Tests that assert
    missing-config behaviour should mark ``no_ai_feature_flag_auto_enable``.
    """
    if request.node.get_closest_marker("postgres") is None:
        yield
        return
    if request.node.get_closest_marker("no_ai_feature_flag_auto_enable") is not None:
        yield
        return

    # Resolve db_session only for postgres tests that request it.
    if "db_session" not in request.fixturenames:
        yield
        return

    db_session: Session = request.getfixturevalue("db_session")

    from sqlalchemy import event, insert, text

    from app.ai_feature_flags.cache import cache_invalidate
    from app.ai_feature_flags.registry import REGISTRY
    from app.db.models.ai_feature_flags import OrganisationAiFeatureFlag
    from app.db.models.organisation import Organisation

    def _after_org_insert(_mapper, connection, target: Organisation) -> None:
        # Seed after the organisation row exists (FK-safe). Uses Core insert so
        # we stay inside the same flush/transaction without recursive ORM flushes.
        # Ensure RLS bypass for seed inserts (tests may have org-scoped RLS active).
        connection.execute(text("SELECT set_config('app.rls_bypass', 'on', true)"))
        rows = []
        for definition in REGISTRY:
            pilot = bool(definition.pilot_eligible)
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "organisation_id": target.id,
                    "feature_id": definition.feature_id,
                    "enabled": True,
                    "pilot_enabled": pilot,
                    "change_reason": "test_auto_enable",
                    "revision": 1,
                    "metadata_json": {},
                }
            )
        connection.execute(insert(OrganisationAiFeatureFlag.__table__), rows)
        cache_invalidate(target.id)

    event.listen(Organisation, "after_insert", _after_org_insert)
    try:
        yield
    finally:
        event.remove(Organisation, "after_insert", _after_org_insert)

