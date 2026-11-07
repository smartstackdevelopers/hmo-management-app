from __future__ import annotations

from fastapi.testclient import TestClient

from app.batch.celery_app import celery_app
from tests.conftest import ORG_A, ORG_B, auth_headers


def test_celery_tasks_registered() -> None:
    assert "hmore.ai.batch.execute_workflow" in celery_app.tasks
    assert "hmore.ai.batch.scheduled_foundation_ping" in celery_app.tasks


def test_batch_submit_eager_completes(client: TestClient) -> None:
    response = client.post(
        "/api/v1/batch/jobs",
        headers=auth_headers(),
        json={"workflow_id": "foundation_ping", "idempotency_key": "once-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["organisation_id"] == str(ORG_A)
    assert body["status"] == "completed"
    assert body["result_ref"]["workflow_id"] == "foundation_ping"


def test_batch_idempotent_resubmit(client: TestClient) -> None:
    headers = auth_headers()
    a = client.post(
        "/api/v1/batch/jobs",
        headers=headers,
        json={"workflow_id": "foundation_ping", "idempotency_key": "dup-key"},
    )
    b = client.post(
        "/api/v1/batch/jobs",
        headers=headers,
        json={"workflow_id": "foundation_ping", "idempotency_key": "dup-key"},
    )
    assert a.json()["job_id"] == b.json()["job_id"]


def test_batch_cross_org_denied(client: TestClient) -> None:
    created = client.post(
        "/api/v1/batch/jobs",
        headers=auth_headers(org_id=ORG_A),
        json={"workflow_id": "foundation_ping"},
    )
    job_id = created.json()["job_id"]
    other = client.get(f"/api/v1/batch/jobs/{job_id}", headers=auth_headers(org_id=ORG_B))
    assert other.status_code == 403


def test_batch_unauthenticated_denied(client: TestClient) -> None:
    response = client.post("/api/v1/batch/jobs", json={"workflow_id": "foundation_ping"})
    assert response.status_code == 401


def test_batch_feature_gate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/batch/jobs",
        headers=auth_headers(features="ai.foundation"),
        json={"workflow_id": "foundation_ping"},
    )
    assert response.status_code == 403
