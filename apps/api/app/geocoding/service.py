"""UK postcode normalisation and live geocoding.

Default provider is postcodes.io (no API key). Pattern matching alone never
proves a postcode is valid — the provider response does.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings, get_settings

logger = logging.getLogger("hmore.geocoding")

# Outward + inward UK postcode shape (spaces optional). Not a validity claim.
_UK_POSTCODE_SHAPE = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GeocodeResult:
    postcode: str
    latitude: float
    longitude: float
    provider: str
    quality: str = "postcode"


def normalize_uk_postcode(raw: str) -> str:
    """Strip, upper-case, and insert the standard inward-code space."""
    compact = re.sub(r"\s+", "", (raw or "").strip().upper())
    if len(compact) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid postcode format",
        )
    return f"{compact[:-3]} {compact[-3:]}"


def looks_like_uk_postcode(raw: str) -> bool:
    compact = re.sub(r"\s+", "", (raw or "").strip().upper())
    spaced = f"{compact[:-3]} {compact[-3:]}" if len(compact) >= 5 else compact
    return bool(_UK_POSTCODE_SHAPE.match(spaced))


def geocode_postcode(raw: str, *, settings: Settings | None = None) -> GeocodeResult:
    """Validate and geocode a UK postcode via the configured provider."""
    cfg = settings or get_settings()
    if not looks_like_uk_postcode(raw):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid postcode format",
        )
    normalised = normalize_uk_postcode(raw)
    provider = (cfg.geocoding_provider or "postcodes_io").strip().lower()
    if provider in {"disabled", "off", "none"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding is not configured",
        )
    if provider == "postcodes_io":
        return _geocode_postcodes_io(normalised, cfg)
    if provider == "nominatim":
        return _geocode_nominatim_postcode(normalised, cfg)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Unsupported geocoding provider: {provider}",
    )


def _geocode_postcodes_io(normalised: str, settings: Settings) -> GeocodeResult:
    base = (settings.geocoding_postcodes_io_base_url or "https://api.postcodes.io").rstrip("/")
    url = f"{base}/postcodes/{normalised.replace(' ', '%20')}"
    try:
        with httpx.Client(timeout=settings.geocoding_timeout_seconds) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        logger.warning("postcodes.io request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service unavailable",
        ) from exc

    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Postcode not found",
        )
    if response.status_code >= 400:
        logger.warning("postcodes.io HTTP %s: %s", response.status_code, response.text[:200])
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service error",
        )
    payload = response.json()
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Postcode not found",
        )
    lat = result.get("latitude")
    lon = result.get("longitude")
    if lat is None or lon is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Postcode has no coordinates",
        )
    return GeocodeResult(
        postcode=str(result.get("postcode") or normalised),
        latitude=float(lat),
        longitude=float(lon),
        provider="postcodes_io",
    )


def _geocode_nominatim_postcode(normalised: str, settings: Settings) -> GeocodeResult:
    """Optional Nominatim fallback. Requires a descriptive User-Agent per Nominatim policy."""
    base = (settings.geocoding_nominatim_base_url or "https://nominatim.openstreetmap.org").rstrip(
        "/"
    )
    headers = {
        "User-Agent": settings.geocoding_nominatim_user_agent
        or "HMore/1.0 (help-near-me; contact=ops@hmore.local)"
    }
    try:
        with httpx.Client(timeout=settings.geocoding_timeout_seconds, headers=headers) as client:
            response = client.get(
                f"{base}/search",
                params={
                    "postalcode": normalised,
                    "countrycodes": "gb",
                    "format": "json",
                    "limit": 1,
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("nominatim request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service unavailable",
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service error",
        )
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Postcode not found",
        )
    row = rows[0]
    return GeocodeResult(
        postcode=normalised,
        latitude=float(row["lat"]),
        longitude=float(row["lon"]),
        provider="nominatim",
    )


def extract_uk_postcode(text: str | None) -> str | None:
    """Best-effort UK postcode extraction from a free-text address."""
    if not text:
        return None
    match = re.search(
        r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
        text.upper(),
    )
    if not match:
        return None
    try:
        return normalize_uk_postcode(match.group(1))
    except HTTPException:
        return None
