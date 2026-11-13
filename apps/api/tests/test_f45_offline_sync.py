"""F4.5 idempotency replay and optimistic concurrency. No database required."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.db.models.enums import HMoreRole
from app.idempotency.service import (
    SCOPE_DAILY_LOG_CREATE,
    apply_idempotent,
    assert_if_match,
    fresh_or_replay,
)
from app.maintenance import service as maintenance_service
from app.maintenance.schemas import CompleteRequest, MaintenanceUpdate, NoteCreate, StatusTransitionRequest
from app.ops import service as ops_service
from app.ops.schemas import VisitUpdate


def _ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_replay_returns_original_resource_and_skips_create() -> None:
    organisation_id, user_id = _ids()
    resource_id = uuid.uuid4()
    session = MagicMock()
    session.scalar.return_value = SimpleNamespace(
        response_snapshot={"status_code": 201, "body": {"id": "orig", "summary": "first"}},
        resource_id=resource_id,
        resource_type="daily_log",
    )
    produce = MagicMock()

    result = apply_idempotent(
        session,
        organisation_id=organisation_id,
        user_id=user_id,
        scope=SCOPE_DAILY_LOG_CREATE,
        key="client-request-1",
        resource_type="daily_log",
        success_status=201,
        produce=produce,
    )

    produce.assert_not_called()
    session.add.assert_not_called()
    assert result.replayed is True
    assert result.status_code == 201
    assert result.body == {"id": "orig", "summary": "first"}
    assert result.resource_id == resource_id
    response = fresh_or_replay(result, {"id": "should-not-be-used"})
    assert response.status_code == 201
    assert json.loads(response.body) == {"id": "orig", "summary": "first"}


def test_duplicate_key_returns_the_first_snapshot() -> None:
    organisation_id, user_id = _ids()
    existing = SimpleNamespace(
        response_snapshot={"status_code": 201, "body": {"id": "orig"}},
        resource_id=uuid.uuid4(),
        resource_type="daily_log",
    )
    session = MagicMock()
    session.scalar.side_effect = [None, existing]
    session.flush.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))
    produce = MagicMock()

    result = apply_idempotent(
        session,
        organisation_id=organisation_id,
        user_id=user_id,
        scope=SCOPE_DAILY_LOG_CREATE,
        key="client-request-1",
        resource_type="daily_log",
        success_status=201,
        produce=produce,
    )

    produce.assert_not_called()
    session.begin_nested.return_value.rollback.assert_called_once()
    assert result.replayed is True
    assert result.status_code == 201
    assert result.body == {"id": "orig"}


def test_first_success_stores_snapshot_and_does_not_claim_replay() -> None:
    organisation_id, user_id = _ids()
    resource_id = uuid.uuid4()
    session = MagicMock()
    session.scalar.return_value = None

    result = apply_idempotent(
        session,
        organisation_id=organisation_id,
        user_id=user_id,
        scope=SCOPE_DAILY_LOG_CREATE,
        key="client-request-1",
        resource_type="daily_log",
        success_status=201,
        produce=lambda: (resource_id, {"id": str(resource_id), "summary": "saved"}),
    )

    stored = session.add.call_args.args[0]
    assert stored.response_snapshot == {
        "status_code": 201,
        "body": {"id": str(resource_id), "summary": "saved"},
    }
    assert stored.resource_id == resource_id
    assert result.replayed is False
    assert result.status_code == 201
    assert fresh_or_replay(result, {"id": "fresh"}) == {"id": "fresh"}


def test_missing_key_does_not_store_a_row() -> None:
    organisation_id, user_id = _ids()
    session = MagicMock()
    resource_id = uuid.uuid4()

    result = apply_idempotent(
        session,
        organisation_id=organisation_id,
        user_id=user_id,
        scope=SCOPE_DAILY_LOG_CREATE,
        key=None,
        resource_type="daily_log",
        success_status=201,
        produce=lambda: (resource_id, {"id": str(resource_id)}),
    )

    session.add.assert_not_called()
    assert result.replayed is False
    assert result.resource_id == resource_id


def test_conflict_returns_409_with_current_updated_at() -> None:
    current = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    stale = current - timedelta(minutes=5)
    with pytest.raises(HTTPException) as exc:
        assert_if_match(current, stale)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "conflict"
    assert exc.value.detail["updated_at"] == current.isoformat()
    assert_if_match(current, None)
    assert_if_match(current, current)
    assert_if_match(current.replace(microsecond=250000), current.replace(microsecond=0))


def test_visit_patch_conflict_does_not_change_the_row(monkeypatch: pytest.MonkeyPatch) -> None:
    current = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(status="scheduled", updated_at=current, completed_at=None)
    monkeypatch.setattr(ops_service, "get_visit", lambda *args, **kwargs: row)
    session = MagicMock()

    with pytest.raises(HTTPException) as exc:
        ops_service.update_visit(
            session,
            MagicMock(),
            uuid.uuid4(),
            VisitUpdate(status="completed", if_match_updated_at=current - timedelta(hours=1)),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["updated_at"] == current.isoformat()
    assert row.status == "scheduled"
    assert row.completed_at is None
    session.flush.assert_not_called()


def test_maintenance_patch_conflict_does_not_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    current = datetime(2026, 11, 10, 15, 30, tzinfo=timezone.utc)
    row = SimpleNamespace(status="submitted", updated_at=current, title="Leak", description="Old")
    monkeypatch.setattr(maintenance_service, "get_request", lambda *args, **kwargs: row)
    ctx = SimpleNamespace(role=HMoreRole.SUPER_ADMIN)
    session = MagicMock()

    with pytest.raises(HTTPException) as exc:
        maintenance_service.update_request(
            session,
            ctx,
            uuid.uuid4(),
            MaintenanceUpdate(title="Changed", if_match_updated_at=current - timedelta(seconds=1)),
        )

    assert exc.value.status_code == 409
    assert row.title == "Leak"
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_work_order_transition_conflict_does_not_change_status(monkeypatch: pytest.MonkeyPatch) -> None:
    current = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        status="submitted",
        updated_at=current,
        requires_approval=False,
        approval_status=None,
    )
    monkeypatch.setattr(maintenance_service, "get_request", lambda *args, **kwargs: row)
    ctx = SimpleNamespace(role=HMoreRole.SUPER_ADMIN)
    session = MagicMock()

    with pytest.raises(HTTPException) as exc:
        maintenance_service.transition_status(
            session,
            ctx,
            row.id,
            StatusTransitionRequest(
                status="acknowledged",
                if_match_updated_at=current - timedelta(minutes=2),
            ),
        )

    assert exc.value.status_code == 409
    assert row.status == "submitted"
    session.add.assert_not_called()


def test_work_order_complete_conflict_does_not_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    current = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(id=uuid.uuid4(), status="in_progress", updated_at=current, assigned_user_id=None)
    monkeypatch.setattr(maintenance_service, "get_request", lambda *args, **kwargs: row)
    ctx = SimpleNamespace(role=HMoreRole.SUPER_ADMIN)
    session = MagicMock()

    with pytest.raises(HTTPException) as exc:
        maintenance_service.complete_request(
            session,
            ctx,
            row.id,
            CompleteRequest(work_notes="Finished the repair", if_match_updated_at=current - timedelta(minutes=2)),
        )

    assert exc.value.status_code == 409
    assert row.status == "in_progress"
    session.add.assert_not_called()


def test_maintenance_note_conflict_does_not_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    current = datetime(2026, 11, 10, 15, 30, tzinfo=timezone.utc)
    row = SimpleNamespace(id=uuid.uuid4(), status="submitted", updated_at=current)
    monkeypatch.setattr(maintenance_service, "get_request", lambda *args, **kwargs: row)
    ctx = SimpleNamespace(role=HMoreRole.SUPER_ADMIN, organisation_id=uuid.uuid4(), user_id=uuid.uuid4())
    session = MagicMock()

    with pytest.raises(HTTPException) as exc:
        maintenance_service.add_note(
            session,
            ctx,
            row.id,
            NoteCreate(body="Still leaking", if_match_updated_at=current - timedelta(minutes=1)),
        )

    assert exc.value.status_code == 409
    session.add.assert_not_called()

