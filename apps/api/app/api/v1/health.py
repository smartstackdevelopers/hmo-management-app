from fastapi import APIRouter

from app import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "hmore-api",
        "version": __version__,
        "api": "v1",
    }
