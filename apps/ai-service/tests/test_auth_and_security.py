from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import ORG_A, ORG_B, USER_A, auth_headers


def test_unauthenticated_workflow_denied(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows/execute",
        json={"workflow_id": "foundation_ping"},
    )
    assert response.status_code == 401


def test_invalid_token_denied(client: TestClient) -> None:
    headers = auth_headers(token="wrong-token")
    response = client.post(
        "/api/v1/workflows/execute",
        headers=headers,
        json={"workflow_id": "foundation_ping"},
    )
    assert response.status_code == 401


def test_missing_org_header_rejected(client: TestClient) -> None:
    headers = auth_headers()
    del headers["X-HMore-Organisation-Id"]
    response = client.post(
        "/api/v1/workflows/execute",
        headers=headers,
        json={"workflow_id": "foundation_ping"},
    )
    assert response.status_code == 422


def test_feature_gate_denies(client: TestClient) -> None:
    headers = auth_headers(features="ai.foundation")
    response = client.post(
        "/api/v1/workflows/execute",
        headers=headers,
        json={"workflow_id": "foundation_ping"},
    )
    assert response.status_code == 403


def test_body_org_impersonation_rejected(client: TestClient) -> None:
    headers = auth_headers(org_id=ORG_A)
    response = client.post(
        "/api/v1/workflows/execute",
        headers=headers,
        json={
            "workflow_id": "foundation_echo",
            "message": "hello",
            "organisation_id": str(ORG_B),
        },
    )
    assert response.status_code == 403


def test_cross_org_approval_isolation(client: TestClient) -> None:
    create = client.post(
        "/api/v1/workflows/execute",
        headers=auth_headers(org_id=ORG_A, user_id=USER_A),
        json={"workflow_id": "foundation_echo", "message": "leak?", "require_human_gate": True},
    )
    assert create.status_code == 200
    approval_id = create.json()["approval_id"]
    assert approval_id

    other = client.get(
        f"/api/v1/approvals/{approval_id}",
        headers=auth_headers(org_id=ORG_B),
    )
    assert other.status_code == 403


def test_provider_secrets_not_in_openapi(client: TestClient) -> None:
    dumped = str(client.get("/openapi.json").json()).lower()
    assert "test-ai-service-token" not in dumped
    assert "sk-live" not in dumped
