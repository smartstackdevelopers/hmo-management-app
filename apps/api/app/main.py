from fastapi import FastAPI

from app import __version__
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_exception_handlers(app)
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "hmore-api", "version": __version__}
