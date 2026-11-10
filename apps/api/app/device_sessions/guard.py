"""Reject API calls whose device session is missing, revoked, lost, or for another user.

A missing ``X-Device-Session-Id`` header is allowed so web clients keep working.
The mobile app sends the header after it has registered a session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.tokens import http_401
from app.db.models.device_sessions import MobileDeviceSession
from app.tenancy.session_rls import apply_platform_rls_bypass

DEVICE_SESSION_REVOKED = "device_session_revoked"
HEADER_NAME = "X-Device-Session-Id"


def enforce_device_session(
    session: Session,
    user_id: uuid.UUID,
    header: str | None,
) -> MobileDeviceSession | None:
    """Return the active session, or None when the caller did not send one.

    Invalid, unknown, revoked, lost, and wrong-user values raise 401
    ``device_session_revoked``. An active match updates ``last_seen_at``.
    """
    if header is None or not str(header).strip():
        return None
    try:
        session_id = uuid.UUID(str(header).strip())
    except ValueError as exc:
        raise http_401(DEVICE_SESSION_REVOKED) from exc

    apply_platform_rls_bypass(session)
    try:
        row = session.get(MobileDeviceSession, session_id)
        if row is None or row.user_id != user_id or row.status != "active":
            raise http_401(DEVICE_SESSION_REVOKED)
        row.last_seen_at = datetime.now(timezone.utc)
        session.flush()
        return row
    finally:
        session.execute(text("SELECT set_config('app.rls_bypass', 'off', true)"))
