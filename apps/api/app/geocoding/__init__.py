"""Configurable postcode / address geocoding for Help Near Me (F5.2)."""

from app.geocoding.service import GeocodeResult, geocode_postcode, normalize_uk_postcode

__all__ = ["GeocodeResult", "geocode_postcode", "normalize_uk_postcode"]
