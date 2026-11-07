from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.errors import ForbiddenError, ValidationServiceError


@dataclass(frozen=True, slots=True)
class TrustedCallerContext:
    """Context derived only after service authentication — never from untrusted body fields."""

    organisation_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    features: frozenset[str] = field(default_factory=frozenset)

    def ensure_org(self, claimed: uuid.UUID | None) -> None:
        """Reject body/query org ids that do not match the trusted header."""
        if claimed is not None and claimed != self.organisation_id:
            raise ForbiddenError("Organisation context mismatch")


def _parse_uuid(value: str | None, label: str) -> uuid.UUID:
    if not value or not value.strip():
        raise ValidationServiceError(f"Trusted header {label} is required")
    try:
        return uuid.UUID(value.strip())
    except ValueError as exc:
        raise ValidationServiceError(f"Trusted header {label} must be a UUID") from exc


def build_trusted_context(
    *,
    organisation_id: str | None,
    user_id: str | None,
    role: str | None,
    features_header: str | None,
    defaults: frozenset[str],
) -> TrustedCallerContext:
    org = _parse_uuid(organisation_id, "X-HMore-Organisation-Id")
    user = _parse_uuid(user_id, "X-HMore-User-Id")
    role_clean = (role or "").strip()
    if not role_clean:
        raise ValidationServiceError("Trusted header X-HMore-Role is required")
    if features_header is None or not features_header.strip():
        features = defaults
    else:
        features = frozenset(part.strip() for part in features_header.split(",") if part.strip())
    return TrustedCallerContext(
        organisation_id=org,
        user_id=user,
        role=role_clean,
        features=features,
    )
