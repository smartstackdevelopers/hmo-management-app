"""Store and replay Idempotency-Key results. Reject stale PATCH writes.

A key is unique for one organisation, one user, and one scope. The first
successful response is stored. A later request with the same key returns that
response and does not run the operation again.

PATCH bodies may include ``if_match_updated_at``. When it differs from the
row's ``updated_at``, the handler raises 409 and leaves the row unchanged.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.idempotency import ClientIdempotencyKey

SCOPE_DAILY_LOG_CREATE = "daily_log.create"
SCOPE_MAINTENANCE_CREATE = "maintenance.create"
SCOPE_VISIT_UPDATE = "visit.update"
SCOPE_TASK_UPDATE = "task.update"
SCOPE_MAINTENANCE_UPDATE = "maintenance.update"
SCOPE_MAINTENANCE_NOTE = "maintenance.note"
SCOPE_MAINTENANCE_TRANSITION = "maintenance.transition"
SCOPE_MAINTENANCE_COMPLETE = "maintenance.complete"

_MAX_KEY_LENGTH = 200


@dataclass(frozen=True)
class IdempotentResult:
    status_code: int
    body: dict[str, Any]
    replayed: bool
    resource_id: uuid.UUID | None = None


def clean_idempotency_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = raw.strip()
    if not key:
        return None
    if len(key) > _MAX_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key is too long",
        )
    return key


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def timestamps_match(current: datetime, expected: datetime) -> bool:
    left = _as_utc(current)
    right = _as_utc(expected)
    if left == right:
        return True
    # Clients often send the server timestamp with the fractional seconds dropped.
    return right.microsecond == 0 and left.replace(microsecond=0) == right.replace(microsecond=0)


def assert_if_match(current: datetime | None, expected: datetime | None) -> None:
    """Raise 409 when the caller sent a timestamp and the row has moved."""
    if expected is None:
        return
    if current is not None and timestamps_match(current, expected):
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "conflict",
            "message": "The record changed on the server. The update was not applied.",
            "updated_at": current.isoformat() if isinstance(current, datetime) else None,
        },
    )


def without_match_field(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("if_match_updated_at", None)
    return body


def _json_default(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Cannot store {type(value).__name__} in an idempotency snapshot")


def jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=_json_default))


def _find(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
    scope: str,
    key: str,
) -> ClientIdempotencyKey | None:
    return session.scalar(
        select(ClientIdempotencyKey).where(
            ClientIdempotencyKey.organisation_id == organisation_id,
            ClientIdempotencyKey.user_id == user_id,
            ClientIdempotencyKey.scope == scope,
            ClientIdempotencyKey.key == key,
        )
    )


def _replay_from(row: ClientIdempotencyKey) -> IdempotentResult | None:
    snapshot = row.response_snapshot
    if not isinstance(snapshot, dict):
        return None
    body = snapshot.get("body")
    if not isinstance(body, dict):
        body = {}
    try:
        status_code = int(snapshot.get("status_code") or 200)
    except (TypeError, ValueError):
        status_code = 200
    return IdempotentResult(
        status_code=status_code,
        body=body,
        replayed=True,
        resource_id=row.resource_id,
    )


def _in_progress() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "in_progress",
            "message": "This request is already being processed.",
        },
    )


def apply_idempotent(
    session: Session,
    *,
    organisation_id: uuid.UUID,
    user_id: uuid.UUID,
    scope: str,
    key: str | None,
    resource_type: str,
    success_status: int,
    produce: Callable[[], tuple[uuid.UUID, dict[str, Any]]],
) -> IdempotentResult:
    """Run ``produce`` once per key. A stored snapshot is returned as-is."""
    normalized = clean_idempotency_key(key)
    claimed: ClientIdempotencyKey | None = None
    if normalized:
        existing = _find(
            session,
            organisation_id=organisation_id,
            user_id=user_id,
            scope=scope,
            key=normalized,
        )
        replay = _replay_from(existing) if existing is not None else None
        if replay is not None:
            return replay
        if existing is not None:
            raise _in_progress()
        claimed = ClientIdempotencyKey(
            organisation_id=organisation_id,
            user_id=user_id,
            scope=scope,
            key=normalized,
            resource_type=resource_type,
            resource_id=None,
            response_snapshot=None,
        )
        nested = session.begin_nested()
        try:
            session.add(claimed)
            session.flush()
            nested.commit()
        except IntegrityError:
            nested.rollback()
            raced = _find(
                session,
                organisation_id=organisation_id,
                user_id=user_id,
                scope=scope,
                key=normalized,
            )
            replay = _replay_from(raced) if raced is not None else None
            if replay is not None:
                return replay
            raise _in_progress() from None

    resource_id, body = produce()
    stored = jsonable(body)
    if not isinstance(stored, dict):
        stored = {"value": stored}
    if claimed is not None:
        claimed.resource_type = resource_type
        claimed.resource_id = resource_id
        claimed.response_snapshot = {"status_code": success_status, "body": stored}
        session.flush()
    return IdempotentResult(
        status_code=success_status,
        body=stored,
        replayed=False,
        resource_id=resource_id,
    )


def fresh_or_replay(result: IdempotentResult, fresh: Any) -> Any:
    """Return the original resource with its original status code on replay."""
    if result.replayed:
        return JSONResponse(status_code=result.status_code, content=result.body)
    return fresh
