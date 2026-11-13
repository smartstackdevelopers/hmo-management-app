"""F7.6 infrastructure preparation checks (no AWS calls)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def test_f76_terraform_production_stack_default_disabled() -> None:
    tfvars = REPO / "infra/aws/terraform/environments/production/terraform.tfvars.example"
    text = tfvars.read_text(encoding="utf-8")
    assert "stack_enabled" in text
    assert "false" in text


def test_f76_dockerfiles_exist() -> None:
    docker = REPO / "infra/docker"
    for name in ("Dockerfile.api", "Dockerfile.ai", "Dockerfile.web", "Dockerfile.worker"):
        assert (docker / name).is_file(), name


def test_f76_sentry_optional_import() -> None:
    from app.core.sentry import init_sentry

    assert init_sentry() is False


def test_f76_production_validation_blocks_memory_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/hmore")
    monkeypatch.setenv("AUTH0_DOMAIN", "example.uk.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example")
    from cryptography.fernet import Fernet

    monkeypatch.setenv("INTEGRATION_SECRETS_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("STORAGE_PROVIDER", "memory")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.hmore.uk")

    from app.core.config import Settings

    errors = Settings().production_validation_errors()
    assert any("memory" in e.lower() for e in errors)

