from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import ORG_A, USER_A, USER_B, auth_headers


def test_foundation_ping(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows/execute",
        headers=auth_headers(),
        json={"workflow_id": "foundation_ping"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["ping"] == "ok"
    assert body["organisation_id"] == str(ORG_A)
    assert body["usage"]["monetary_cost"] is None
    assert "X-Correlation-Id" in response.headers


def test_foundation_echo_uses_prompt_version(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows/execute",
        headers=auth_headers(),
        json={"workflow_id": "foundation_echo", "message": "water leak under sink"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["tool_output"] == "water leak under sink"
    assert body["result"]["prompt_id"] == "hmore.foundation.echo"
    assert body["result"]["prompt_version"] == "1.0.0"
    assert body["requires_approval"] is False


def test_unsupported_workflow(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows/execute",
        headers=auth_headers(),
        json={"workflow_id": "notes_analysis"},
    )
    assert response.status_code == 404


def test_human_approval_gate_and_decide(client: TestClient) -> None:
    create = client.post(
        "/api/v1/workflows/execute",
        headers=auth_headers(user_id=USER_A),
        json={
            "workflow_id": "foundation_echo",
            "message": "needs approval",
            "require_human_gate": True,
        },
    )
    assert create.status_code == 200
    body = create.json()
    assert body["requires_approval"] is True
    assert body["status"] == "awaiting_human_approval"
    approval_id = body["approval_id"]

    # AI suggestion source remains distinguishable
    pending = client.get(f"/api/v1/approvals/{approval_id}", headers=auth_headers(user_id=USER_A))
    assert pending.status_code == 200
    assert pending.json()["proposed_action_source"] == "ai_suggestion"
    assert pending.json()["is_human_approved"] is False

    decided = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        headers=auth_headers(user_id=USER_B),
        json={"approve": True, "note": "looks fine"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"
    assert decided.json()["is_human_approved"] is True
    assert decided.json()["reviewer_user_id"] == str(USER_B)


def test_invalid_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows/execute",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 422
