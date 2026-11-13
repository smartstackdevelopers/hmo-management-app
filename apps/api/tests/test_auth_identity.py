"""Identity mapping tests. Require PostgreSQL when DATABASE_URL is set."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.identity import resolve_user_from_claims
from app.db.models import User


pytestmark = pytest.mark.postgres


def test_provision_user_from_subject(db_session: Session) -> None:
    subject = f"auth0|{uuid.uuid4()}"
    user = resolve_user_from_claims(
        db_session,
        {
            "sub": subject,
            "email": f"{uuid.uuid4().hex}@example.com",
            "email_verified": True,
            "name": "Priya Nair",
        },
    )
    assert user.external_subject == subject
    assert user.display_name == "Priya Nair"
    again = resolve_user_from_claims(
        db_session,
        {"sub": subject, "email": user.email, "name": "Priya Nair"},
    )
    assert again.id == user.id


def test_reject_email_linked_to_other_subject(db_session: Session) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    first = User(
        external_subject=f"auth0|{uuid.uuid4()}",
        email=email,
        display_name="Existing",
    )
    db_session.add(first)
    db_session.flush()

    with pytest.raises(HTTPException) as exc:
        resolve_user_from_claims(
            db_session,
            {
                "sub": f"auth0|{uuid.uuid4()}",
                "email": email,
                "email_verified": True,
            },
        )
    assert exc.value.status_code == 409

