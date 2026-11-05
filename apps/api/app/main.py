from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.security_headers import SecurityHeadersMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Organisation-Id", "X-HMore-Role", "X-Correlation-Id"],
)

register_exception_handlers(app)
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "hmore-api", "version": __version__}
