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
