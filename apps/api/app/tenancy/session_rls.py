"""Transaction-scoped PostgreSQL RLS context helpers (defence in depth).

SET LOCAL is transaction-scoped and does not leak across pooled connections after
commit/rollback. Application-layer filters remain mandatory; RLS is additional.

Superusers bypass RLS even with FORCE. Organisation-scoped requests therefore
SET LOCAL ROLE to hmore_app (non-superuser) so policies apply.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

APP_ROLE = "hmore_app"


def clear_rls_context(session: Session) -> None:
    session.execute(text("RESET ROLE"))
    session.execute(text("SELECT set_config('app.organisation_id', '', true)"))
    session.execute(text("SELECT set_config('app.rls_bypass', 'off', true)"))


def apply_organisation_rls(session: Session, organisation_id: uuid.UUID) -> None:
    """Constrain RLS to one organisation for the current transaction."""
    session.execute(text(f"SET LOCAL ROLE {APP_ROLE}"))
    session.execute(text("SELECT set_config('app.rls_bypass', 'off', true)"))
    session.execute(
        text("SELECT set_config('app.organisation_id', :org_id, true)"),
        {"org_id": str(organisation_id)},
    )


def apply_platform_rls_bypass(session: Session) -> None:
    """Explicit Super Admin / system bypass for the current transaction only."""
    session.execute(text("RESET ROLE"))
    session.execute(text("SELECT set_config('app.rls_bypass', 'on', true)"))
    session.execute(text("SELECT set_config('app.organisation_id', '', true)"))
