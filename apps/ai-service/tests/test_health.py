from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_compiles_langgraph_foundation() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "hmore-ai"
    assert body["graph"] == "ok"


def test_v1_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["api"] == "v1"


def test_ready() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_openapi_available() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "paths" in spec
    assert "/api/v1/workflows/execute" in spec["paths"]
