"""Prompt 12 unit tests that do not require a live Postgres (hashing, tokens, policies)."""

from __future__ import annotations

import pytest

from app.auth.native_service import PUBLIC_REGISTER_ROLES
from app.auth.native_tokens import (
    NATIVE_ISS,
    decode_native_access_token,
    hash_token,
    issue_access_token,
    native_subject_for_user,
)
from app.auth.passwords import hash_password, verify_password
from app.core.config import Settings
from app.db.models import HMoreRole
from uuid import uuid4


def test_password_hash_and_verify_roundtrip():
    hashed = hash_password("CorrectHorseBattery1")
    assert hashed != "CorrectHorseBattery1"
    assert verify_password(hashed, "CorrectHorseBattery1") is True
    assert verify_password(hashed, "wrong-password") is False


def test_password_rejects_short_secrets():
    with pytest.raises(ValueError):
        hash_password("short")


def test_native_access_token_roundtrip():
    settings = Settings(
        ENVIRONMENT="development",
        HMORE_NATIVE_AUTH=True,
        HMORE_NATIVE_AUTH_SECRET="unit-test-native-secret-value",
        HMORE_NATIVE_AUDIENCE="https://api.hmore.local",
        HMORE_ALLOW_AUTH0=False,
    )
    user_id = uuid4()
    token, ttl = issue_access_token(
        settings=settings,
        user_id=user_id,
        email="unit@hmore.local",
        authorization_version=1,
    )
    assert ttl >= 60
    claims = decode_native_access_token(token, settings)
    assert claims is not None
    assert claims["sub"] == native_subject_for_user(user_id)
    assert claims["email"] == "unit@hmore.local"
    assert claims["iss"] == NATIVE_ISS
    assert claims["hmore_native"] is True


def test_refresh_token_hash_is_one_way():
    raw = "refresh-token-value"
    digest = hash_token(raw)
    assert digest != raw
    assert len(digest) == 64
    assert hash_token(raw) == digest


def test_public_register_roles_exclude_privileged():
    assert HMoreRole.SUPER_ADMIN not in PUBLIC_REGISTER_ROLES
    assert HMoreRole.ORGANISATION_ADMIN not in PUBLIC_REGISTER_ROLES
    assert HMoreRole.TENANT in PUBLIC_REGISTER_ROLES
    assert len(PUBLIC_REGISTER_ROLES) == 4
