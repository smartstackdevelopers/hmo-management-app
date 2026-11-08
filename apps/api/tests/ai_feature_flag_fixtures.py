"""Helpers so Phase 3 AI tests keep working under F3.15 fail-closed flags."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_feature_flags.cache import cache_invalidate
from app.ai_feature_flags.registry import REGISTRY
from app.db.models.ai_feature_flags import OrganisationAiFeatureFlag
from app.db.models.organisation import Organisation


def enable_all_controllable_ai_features(
    session: Session,
    organisation_id: uuid.UUID,
    *,
    include_tenant_assistant_pilot: bool = True,
) -> None:
    """Enable registered AI features for a test organisation (preserves pre-F3.15 access)."""
    for definition in REGISTRY:
        pilot = bool(definition.pilot_eligible and include_tenant_assistant_pilot)
        existing = session.scalars(
            select(OrganisationAiFeatureFlag).where(
                OrganisationAiFeatureFlag.organisation_id == organisation_id,
                OrganisationAiFeatureFlag.feature_id == definition.feature_id,
            )
        ).first()
        if existing is None:
            session.add(
                OrganisationAiFeatureFlag(
                    id=uuid.uuid4(),
                    organisation_id=organisation_id,
                    feature_id=definition.feature_id,
                    enabled=True,
                    pilot_enabled=pilot,
                    change_reason="test_auto_enable",
                    revision=1,
                )
            )
        else:
            existing.enabled = True
            existing.pilot_enabled = pilot
            existing.change_reason = "test_auto_enable"
    # Do not flush here — callers may invoke this from before_flush.
    cache_invalidate(organisation_id)


def enable_ai_features_for_all_orgs_in_session(
    session: Session,
    *,
    include_tenant_assistant_pilot: bool = True,
) -> None:
    org_ids = list(session.scalars(select(Organisation.id)))
    for org_id in org_ids:
        enable_all_controllable_ai_features(
            session,
            org_id,
            include_tenant_assistant_pilot=include_tenant_assistant_pilot,
        )
