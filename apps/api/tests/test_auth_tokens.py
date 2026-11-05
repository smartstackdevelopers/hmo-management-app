"""Mocked Auth0 JWKS tests. These do not call a real Auth0 tenant."""

from __future__ import annotations

import time
import uuid
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth.jwks import clear_jwks_cache, set_jwks_for_tests
from app.auth.tokens import TokenValidationError, token_has_mfa, validate_access_token
from app.core.config import Settings, get_settings
from app.main import app


DOMAIN = "hmore-test.uk.auth0.com"
ISSUER = f"https://{DOMAIN}/"
AUDIENCE = "https://api.hmore.local"
KID = "test-key-1"


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[Any, Any]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(scope="module")
def jwks(rsa_keys: tuple[Any, Any]) -> dict[str, Any]:
    _, public_key = rsa_keys
    public_numbers = public_key.public_numbers()

    def b64url_uint(value: int) -> str:
        length = (value.bit_length() + 7) // 8
        return jwt.utils.base64url_encode(value.to_bytes(length, "big")).decode("ascii")

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": KID,
                "use": "sig",
                "alg": "RS256",
                "n": b64url_uint(public_numbers.n),
                "e": b64url_uint(public_numbers.e),
            }
        ]
    }


@pytest.fixture(autouse=True)
def auth_settings(jwks: dict[str, Any], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH0_DOMAIN", DOMAIN)
    monkeypatch.setenv("AUTH0_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("AUTH0_ISSUER", ISSUER)
    monkeypatch.setenv("AUTH0_REQUIRE_MFA_CLAIM", "false")
    get_settings.cache_clear()
    clear_jwks_cache()
    set_jwks_for_tests(jwks)
    yield
    clear_jwks_cache()
    get_settings.cache_clear()


def _settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


def _sign(
    private_key: Any,
    *,
    aud: str = AUDIENCE,
    iss: str = ISSUER,
    exp_delta: int = 3600,
    sub: str = "auth0|user-1",
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + exp_delta,
    }
    if extra:
        payload.update(extra)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem, algorithm="RS256", headers={"kid": KID})


def test_valid_token_accepted(rsa_keys: tuple[Any, Any]) -> None:
    private_key, _ = rsa_keys
    token = _sign(private_key)
    claims = validate_access_token(token, _settings())
    assert claims["sub"] == "auth0|user-1"
    assert claims["aud"] == AUDIENCE


def test_invalid_signature_rejected(rsa_keys: tuple[Any, Any]) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _sign(other)
    with pytest.raises(TokenValidationError):
        validate_access_token(token, _settings())


def test_wrong_issuer_rejected(rsa_keys: tuple[Any, Any]) -> None:
    private_key, _ = rsa_keys
    token = _sign(private_key, iss="https://evil.example/")
    with pytest.raises(TokenValidationError):
        validate_access_token(token, _settings())


def test_wrong_audience_rejected(rsa_keys: tuple[Any, Any]) -> None:
    private_key, _ = rsa_keys
    token = _sign(private_key, aud="https://other.api")
    with pytest.raises(TokenValidationError):
        validate_access_token(token, _settings())


def test_expired_token_rejected(rsa_keys: tuple[Any, Any]) -> None:
    private_key, _ = rsa_keys
    token = _sign(private_key, exp_delta=-10)
    with pytest.raises(TokenValidationError):
        validate_access_token(token, _settings())


def test_missing_authorization_rejected() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_invalid_bearer_rejected(rsa_keys: tuple[Any, Any]) -> None:
    private_key, _ = rsa_keys
    token = _sign(private_key, aud="https://wrong")
    client = TestClient(app)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_mfa_claim_detection(rsa_keys: tuple[Any, Any]) -> None:
    private_key, _ = rsa_keys
    with_mfa = validate_access_token(
        _sign(private_key, extra={"amr": ["mfa"]}),
        _settings(),
    )
    without = validate_access_token(_sign(private_key, sub="auth0|user-2"), _settings())
    assert token_has_mfa(with_mfa) is True
    assert token_has_mfa(without) is False


def test_mfa_policy_enforced_when_configured(
    rsa_keys: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.auth.deps import enforce_mfa_policy
    from fastapi import HTTPException

    monkeypatch.setenv("AUTH0_REQUIRE_MFA_CLAIM", "true")
    get_settings.cache_clear()
    private_key, _ = rsa_keys
    claims = validate_access_token(_sign(private_key), _settings())
    with pytest.raises(HTTPException) as exc:
        enforce_mfa_policy(claims, _settings())
    assert exc.value.status_code == 403

    mfa_claims = validate_access_token(
        _sign(private_key, sub=f"auth0|{uuid.uuid4()}", extra={"amr": ["mfa"]}),
        _settings(),
    )
    enforce_mfa_policy(mfa_claims, _settings())
