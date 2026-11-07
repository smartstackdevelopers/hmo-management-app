from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.correlation import get_correlation_id, set_correlation_id
from app.core.errors import AiServiceError, safe_error_body
from app.core.logging import configure_logging, get_logger
from app.graph.foundation import ping_graph

_boot = get_settings()
configure_logging(_boot.log_level)
logger = get_logger("hmore.ai")

app = FastAPI(
    title=_boot.app_name,
    version=__version__,
    description=(
        "HMore shared AI service (F3.1). Server-to-server access only. "
        "Core FastAPI remains authoritative for business records and permissions."
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.middleware("http")
async def correlation_and_limits(request: Request, call_next):
    settings = get_settings()
    cid = set_correlation_id(request.headers.get("X-Correlation-Id"))
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > settings.max_request_bytes:
            return JSONResponse(
                status_code=413,
                content={"error": "payload_too_large", "message": "Request body exceeds size limit"},
                headers={"X-Correlation-Id": cid},
            )
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    return response


@app.exception_handler(AiServiceError)
async def ai_service_error_handler(_: Request, exc: AiServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=safe_error_body(exc),
        headers={"X-Correlation-Id": get_correlation_id()},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": "Invalid request payload"},
        headers={"X-Correlation-Id": get_correlation_id()},
    )


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error type=%s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"},
        headers={"X-Correlation-Id": get_correlation_id()},
    )


def _health_payload() -> dict[str, str]:
    try:
        graph_status = ping_graph()
    except Exception as exc:  # noqa: BLE001
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


@app.get("/ready")
def ready() -> JSONResponse:
    settings = get_settings()
    try:
        ping_graph()
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "graph_compile_failed"})
    if settings.environment == "production" and not settings.service_auth_configured:
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "ai_service_token_missing"})
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "llm_provider": settings.llm_provider},
    )


app.include_router(v1_router, prefix=_boot.api_v1_prefix)
