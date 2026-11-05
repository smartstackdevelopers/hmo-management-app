from fastapi import FastAPI, HTTPException

from app import __version__
from app.core.config import get_settings
from app.graph.foundation import ping_graph

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


def _health_payload() -> dict[str, str]:
    try:
        graph_status = ping_graph()
    except Exception as exc:  # noqa: BLE001 — surface graph compile failures
        raise HTTPException(
            status_code=503,
            detail={"error": "AI foundation graph failed", "reason": type(exc).__name__},
        ) from exc
    return {
        "status": "ok",
        "service": "hmore-ai",
        "version": __version__,
        "graph": graph_status,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return _health_payload()


@app.get(f"{settings.api_v1_prefix}/health")
def v1_health() -> dict[str, str]:
    payload = _health_payload()
    payload["api"] = "v1"
    return payload
