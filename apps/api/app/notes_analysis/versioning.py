"""Source note version fingerprint for F3.4 analysis consistency."""

from __future__ import annotations

import hashlib

from app.db.models.support_ops import DailyLog


def source_note_version(log: DailyLog) -> str:
    """Stable fingerprint of the note content + last update time.

    If the note changes, the fingerprint changes so prior analyses cannot
    silently appear as analysis of the new content.
    """
    updated = log.updated_at.isoformat() if log.updated_at else ""
    material = "|".join(
        [
            str(log.id),
            str(log.status),
            log.summary or "",
            log.notes or "",
            log.activity_category or "",
            log.interaction_type or "",
            "1" if log.follow_up_required else "0",
            log.next_action or "",
            updated,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def note_payload_for_ai(log: DailyLog) -> dict:
    """Minimised authorised fields sent to the AI service — no extra tenant PII."""
    return {
        "daily_log_id": str(log.id),
        "log_date": log.log_date.isoformat() if log.log_date else None,
        "activity_category": log.activity_category,
        "summary": log.summary,
        "notes": (log.notes or "")[:4000],
        "interaction_type": log.interaction_type,
        "follow_up_required": log.follow_up_required,
        "next_action": log.next_action,
        "status": log.status,
        "source_note_version": source_note_version(log),
    }
