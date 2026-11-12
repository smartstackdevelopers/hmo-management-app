"""F1.11 configuration, secret redaction, and security-header tests.

These tests do **not** prove AWS KMS or RDS encryption is active in a live account.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.secrets import REDACTED, redact_database_url, redact_mapping, redact_text
from app.main import app


def test_production_requires_critical_settings() -> None:
    settings = Settings(
        environment="production",
        database_url=None,
        auth0_domain=None,
        auth0_audience=None,
        storage_provider="memory",
        cors_allowed_origins="*",
        integration_secrets_key=None,
    )
    errors = settings.production_validation_errors()
    assert any("DATABASE_URL" in item for item in errors)
    assert any("AUTH0_DOMAIN" in item for item in errors)
    assert any("AUTH0_AUDIENCE" in item for item in errors)
    assert any("INTEGRATION_SECRETS_KEY" in item for item in errors)
    assert any("memory" in item for item in errors)
    assert any("'*'" in item or "*" in item for item in errors)


def test_production_accepts_iam_style_s3_without_static_keys() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://hmore:hmore@db:5432/hmore",
        auth0_domain="example.uk.auth0.com",
        auth0_audience="https://api.hmore.example",
        storage_provider="s3",
        s3_bucket="hmore-private",
        s3_access_key_id=None,
        s3_secret_access_key=None,
        cors_allowed_origins="https://app.hmore.example",
        enforce_https_origins=True,
        integration_secrets_key="dGVzdC1rZXktMzItYnl0ZXMtZm9yLWZlcm5ldCEhIQ==",
    )
    assert settings.production_validation_errors() == []


def test_production_rejects_partial_s3_keys_and_http_origins() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://hmore:hmore@db:5432/hmore",
        auth0_domain="example.uk.auth0.com",
        auth0_audience="https://api.hmore.example",
        storage_provider="s3",
        s3_bucket="hmore-private",
        s3_access_key_id="AKIAEXAMPLE",
        s3_secret_access_key=None,
        cors_allowed_origins="http://app.hmore.example",
        integration_secrets_key="dGVzdC1rZXktMzItYnl0ZXMtZm9yLWZlcm5ldCEhIQ==",
    )
    errors = settings.production_validation_errors()
    assert any("both be set or both omitted" in item for item in errors)
    assert any("Insecure CORS" in item for item in errors)


def test_development_does_not_require_production_secrets() -> None:
    settings = Settings(environment="development", database_url=None)
    assert settings.production_validation_errors() == []
    # assert_safe_for_runtime must not raise in development
    settings.assert_safe_for_runtime()


def test_secret_redaction_helpers() -> None:
    cleaned = redact_mapping(
        {
            "password": "secret",
            "Authorization": "Bearer abc.def",
            "safe": "ok",
            "nested": {"refresh_token": "xyz"},
        }
    )
    assert cleaned["password"] == REDACTED
    assert cleaned["Authorization"] == REDACTED
    assert cleaned["safe"] == "ok"
    assert cleaned["nested"]["refresh_token"] == REDACTED
    assert REDACTED in redact_text("Authorization: Bearer abc.def.ghi")
    assert "hmore:hmore@" not in (redact_database_url(
        "postgresql+psycopg://hmore:hmore@localhost:5432/hmore"
    ) or "")


def test_security_headers_present_on_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_env_example_files_are_placeholders_only() -> None:
    """Heuristic: committed examples must not look like live AWS/Auth0 secrets."""
    root = Path(__file__).resolve().parents[3]
    examples = [
        root / ".env.example",
        root / "apps" / "api" / ".env.example",
        root / "apps" / "web" / ".env.example",
    ]
    # Build markers without embedding a contiguous PEM header (CI secrets hygiene).
    pem_marker = "-----BEGIN " + "PRIVATE KEY-----"
    banned_substrings = [
        "AKIA",  # typical AWS access key prefix
        "sk_live_",
        pem_marker,
    ]
    for path in examples:
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        for banned in banned_substrings:
            assert banned not in text, f"{path} contains forbidden marker {banned}"
        # AUTH0_SECRET should be empty or commented placeholder, not a long hex blob
        for line in text.splitlines():
            if line.startswith("AUTH0_SECRET=") and not line.strip().endswith("="):
                value = line.split("=", 1)[1].strip().strip('"')
                assert len(value) < 16 or value.startswith("change") or "rand" in value.lower()


def test_gitignore_covers_dotenv() -> None:
    root = Path(__file__).resolve().parents[3]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore


def test_auth_failure_response_is_generic() -> None:
    """Invalid tokens must not leak JWT validation internals in HTTP bodies."""
    from unittest.mock import patch

    from app.auth.tokens import TokenValidationError

    client = TestClient(app)
    with patch(
        "app.auth.deps.validate_access_token",
        side_effect=TokenValidationError("Signing key not found in JWKS"),
    ):
        response = client.get(
            "/api/v1/isolation/properties",
            headers={"Authorization": "Bearer synthetic-token"},
        )
    assert response.status_code == 401
    detail = response.json().get("detail")
    assert detail == "Invalid or missing access token"
    assert "JWKS" not in str(detail)
