"""F2.11 document expiry reminder scheduling (ReminderRecord + F2.2 dispatch)."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.managed_documents import ManagedDocument, OrganisationDocumentSettings
from app.db.models.organisation import Organisation
from app.db.models.scheduling import ReminderRecord
from app.managed_documents import access as md_access
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass


def _floor_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def expected_reminder_kind_for_doc(
    doc: ManagedDocument,
    settings: OrganisationDocumentSettings,
) -> str | None:
    """Return ReminderRecord.reminder_kind if a reminder should fire now, else None."""
    if doc.status != "active" or doc.uploaded_by_user_id is None:
        return None
    if doc.expiry_date is None:
        return None
    today = _today()
    ed = doc.expiry_date
    first_days = settings.expiry_reminder_days_first
    urgent_days = settings.expiry_reminder_days_urgent
    if ed < today:
        if (today - ed).days > 30:
            return None
        return "document_expired"
    days_to = (ed - today).days
    if days_to <= urgent_days:
        return "document_expiring_urgent"
    if days_to <= first_days:
        return "document_expiring_soon"
    return None


def scan_and_schedule_document_reminders(session: Session) -> dict[str, int]:
    """Insert ReminderRecord rows for document expiry windows (idempotent via unique constraint)."""
    apply_platform_rls_bypass(session)
    now = datetime.now(timezone.utc)
    bucket = _floor_hour(now)
    counts = {"scheduled": 0}

    org_ids = list(session.scalars(select(Organisation.id)))
    for org_id in org_ids:
        apply_organisation_rls(session, org_id)
        settings = md_access.get_or_create_settings(session, org_id)

        docs = list(
            session.scalars(
                select(ManagedDocument).where(
                    ManagedDocument.organisation_id == org_id,
                    ManagedDocument.expiry_date.is_not(None),
                )
            )
        )
        for d in docs:
            kind = expected_reminder_kind_for_doc(d, settings)
            if kind is None:
                continue

            exists = session.scalar(
                select(ReminderRecord.id).where(
                    ReminderRecord.organisation_id == org_id,
                    ReminderRecord.resource_type == "managed_document",
                    ReminderRecord.resource_id == d.id,
                    ReminderRecord.reminder_kind == kind,
                    ReminderRecord.scheduled_for == bucket,
                )
            )
            if exists:
                continue

            summary_bits = [f"Document {d.reference_number}"]
            if d.expiry_date:
                summary_bits.append(f"expiry {d.expiry_date.isoformat()}")
            summary_bits.append(kind.replace("document_", "").replace("_", " "))
            payload_summary = " — ".join(summary_bits)[:255]

            row = ReminderRecord(
                organisation_id=org_id,
                resource_type="managed_document",
                resource_id=d.id,
                reminder_kind=kind,
                recipient_user_id=d.uploaded_by_user_id,
                scheduled_for=bucket,
                status="pending",
                channel="in_app",
                payload_summary=payload_summary,
            )
            session.add(row)
            counts["scheduled"] += 1

    session.flush()
    return counts
