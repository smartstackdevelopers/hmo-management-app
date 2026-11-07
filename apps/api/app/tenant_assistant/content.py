"""Retrieve only explicitly approved tenant-facing content.

Sources (existing HMore approval mechanisms — not invented policy):
- F2.12 CommunicationAnnouncement: status=published, tenant-facing audience,
  not expired/cancelled/draft.
- F2.8 MaintenanceEmergencyContent: approved_for_use=True.

Private notes, staff-only announcements, drafts, and unapproved emergency text
are never included.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.communication import CommunicationAnnouncement
from app.db.models.maintenance import MaintenanceEmergencyContent

_TOKEN = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)

# In-process approved-content pack cache: org-scoped, fingerprint-keyed.
_CACHE: dict[str, tuple[float, str, list["ApprovedContentItem"]]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 300.0

TENANT_AUDIENCES = frozenset({"tenants_only", "organisation_all"})


@dataclass(frozen=True)
class ApprovedContentItem:
    content_id: str
    source_type: str
    title: str
    body: str
    version_token: str
    organisation_id: str
    approved_at: str | None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def content_fingerprint(items: list[ApprovedContentItem]) -> str:
    material = "|".join(sorted(f"{i.content_id}:{i.version_token}" for i in items))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def invalidate_org_content_cache(organisation_id: UUID) -> None:
    prefix = f"{organisation_id}:"
    with _CACHE_LOCK:
        for key in list(_CACHE.keys()):
            if key.startswith(prefix):
                del _CACHE[key]


def _load_announcements(session: Session, organisation_id: UUID, user_id: UUID) -> list[ApprovedContentItem]:
    now = _now()
    rows = list(
        session.scalars(
            select(CommunicationAnnouncement).where(
                CommunicationAnnouncement.organisation_id == organisation_id,
                CommunicationAnnouncement.status == "published",
                or_(
                    CommunicationAnnouncement.expires_at.is_(None),
                    CommunicationAnnouncement.expires_at > now,
                ),
            )
        )
    )
    items: list[ApprovedContentItem] = []
    for row in rows:
        if row.audience == "staff_only" or row.audience == "landlords_only":
            continue
        if row.audience == "custom_users":
            ids = row.audience_user_ids or []
            if user_id not in ids:
                continue
        elif row.audience not in TENANT_AUDIENCES:
            continue
        version = (row.published_at or row.updated_at or row.created_at).isoformat()
        items.append(
            ApprovedContentItem(
                content_id=str(row.id),
                source_type="communication_announcement",
                title=row.title,
                body=row.body,
                version_token=version,
                organisation_id=str(organisation_id),
                approved_at=row.published_at.isoformat() if row.published_at else None,
            )
        )
    return items


def _load_emergency(session: Session, organisation_id: UUID) -> list[ApprovedContentItem]:
    rows = list(
        session.scalars(
            select(MaintenanceEmergencyContent).where(
                MaintenanceEmergencyContent.organisation_id == organisation_id,
                MaintenanceEmergencyContent.approved_for_use.is_(True),
            )
        )
    )
    items: list[ApprovedContentItem] = []
    for row in rows:
        version = row.updated_at.isoformat() if row.updated_at else row.created_at.isoformat()
        items.append(
            ApprovedContentItem(
                content_id=str(row.id),
                source_type="maintenance_emergency_content",
                title=row.title,
                body=row.body,
                version_token=version,
                organisation_id=str(organisation_id),
                approved_at=version,
            )
        )
    return items


def load_approved_content(
    session: Session,
    organisation_id: UUID,
    user_id: UUID,
) -> tuple[list[ApprovedContentItem], str]:
    """Return approved items and fingerprint. Cache keyed by org + fingerprint."""
    announcements = _load_announcements(session, organisation_id, user_id)
    emergency = _load_emergency(session, organisation_id)
    items = announcements + emergency
    fingerprint = content_fingerprint(items)
    cache_key = f"{organisation_id}:{fingerprint}"
    now = time.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[2], cached[1]
        _CACHE[cache_key] = (now, fingerprint, items)
    return items, fingerprint


def score_relevance(question: str, item: ApprovedContentItem) -> float:
    q_tokens = set(_TOKEN.findall(question.lower()))
    if not q_tokens:
        return 0.0
    text = f"{item.title} {item.body}".lower()
    hits = sum(1 for token in q_tokens if token in text)
    return hits / max(len(q_tokens), 1)


def select_relevant(
    question: str,
    items: list[ApprovedContentItem],
    *,
    limit: int = 5,
    min_score: float = 0.15,
) -> list[ApprovedContentItem]:
    ranked = sorted(
        ((score_relevance(question, item), item) for item in items),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [item for score, item in ranked if score >= min_score][:limit]


def items_as_dicts(items: list[ApprovedContentItem]) -> list[dict[str, Any]]:
    return [
        {
            "content_id": item.content_id,
            "source_type": item.source_type,
            "title": item.title,
            "body": item.body[:2000],
            "version_token": item.version_token,
            "organisation_id": item.organisation_id,
            "approved_at": item.approved_at,
        }
        for item in items
    ]


ESCALATION_HINTS = (
    "my application",
    "am i eligible",
    "approve my",
    "reject my",
    "another tenant",
    "someone else's",
    "case note",
    "safeguarding",
    "emergency",
    "danger",
    "i want to complain",
    "change my support plan",
    "cancel my appointment",
    "legal advice",
    "medical advice",
)


def detect_escalation(question: str) -> str | None:
    lowered = question.lower()
    if any(h in lowered for h in ("emergency", "danger", "fire", "gas leak", "immediate harm")):
        return "emergency_or_safety"
    if any(h in lowered for h in ("eligible", "approve my application", "reject my application", "housing decision")):
        return "housing_decision"
    if "another tenant" in lowered or "someone else's" in lowered:
        return "other_tenant"
    if "safeguarding" in lowered:
        return "safeguarding"
    if "case note" in lowered or "staff note" in lowered:
        return "private_records"
    if "support plan" in lowered and any(w in lowered for w in ("change", "update", "modify", "delete")):
        return "record_change"
    if "complain" in lowered or "complaint" in lowered:
        return "complaint_escalation"
    for hint in ESCALATION_HINTS:
        if hint in lowered:
            return "human_support"
    return None
