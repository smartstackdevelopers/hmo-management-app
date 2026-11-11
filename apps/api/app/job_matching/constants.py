"""Shared F5.4 job matching constants."""

from __future__ import annotations

EMPLOYMENT_TYPES = (
    "full_time",
    "part_time",
    "temporary",
    "permanent",
    "apprenticeship",
    "internship",
    "volunteer",
)

SOURCE_CATALOGUE = "hmore_catalogue"
SOURCE_ADZUNA = "adzuna"
SOURCE_REED = "reed"
SOURCE_STRUCTURED_IMPORT = "structured_import"

EMBEDDING_DIM = 128

# Match scoring is advisory only — never a guarantee of employment.
SCORE_DISCLAIMER = (
    "Match scores are advisory based on skills and preferences you provided. "
    "They are not a guarantee of employment and do not use protected personal characteristics."
)
