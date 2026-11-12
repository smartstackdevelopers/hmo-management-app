"""Council Portal request context — separate from OrganisationContext / HMoreRole."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.db.models.user import User


@dataclass(frozen=True)
class CouncilPortalContext:
    """Authenticated council officer viewing a specific organisation via add-on grant."""

    user: User
    organisation_id: uuid.UUID
    officer_id: uuid.UUID
    addon_role_label: str = "council_officer"

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id
