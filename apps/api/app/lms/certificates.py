"""F8.4 certificate PDF and verification."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.lms import LmsCertificate, LmsCourse, LmsEnrollment
from app.db.models.user import User
from app.evidence.pdf import build_simple_pdf
from app.lms.constants import ADDON_DISCLAIMER


def _now() -> datetime:
    return datetime.now(timezone.utc)


def verification_ref() -> str:
    return secrets.token_urlsafe(24)[:48]


def next_certificate_number(session: Session, org_id: uuid.UUID) -> str:
    year = _now().year
    prefix = f"CERT-{year}-"
    n = (
        session.scalar(
            select(func.count()).select_from(LmsCertificate).where(
                LmsCertificate.organisation_id == org_id,
                LmsCertificate.certificate_number.like(f"{prefix}%"),
            )
        )
        or 0
    )
    return f"{prefix}{n + 1:06d}"


def build_certificate_pdf(cert: LmsCertificate) -> bytes:
    lines = [
        f"Certificate: {cert.certificate_number}",
        f"Learner: {cert.learner_name}",
        f"Course: {cert.course_title}",
        f"Issued: {cert.issued_at.date().isoformat()}",
        f"Verification reference: {cert.verification_reference}",
        f"Status: {cert.status}",
        ADDON_DISCLAIMER,
    ]
    if cert.expires_at:
        lines.append(f"Valid until: {cert.expires_at.date().isoformat()}")
    return build_simple_pdf("Training certificate", lines)


def issue_certificate(
    session: Session,
    *,
    org_id: uuid.UUID,
    enrollment: LmsEnrollment,
    course: LmsCourse,
    learner: User,
    provider_name: str | None,
    validity_days: int | None,
) -> LmsCertificate:
    existing = session.scalar(select(LmsCertificate).where(LmsCertificate.enrollment_id == enrollment.id))
    if existing and existing.status != "revoked":
        return existing
    expires = _now() + timedelta(days=validity_days) if validity_days else None
    cert = LmsCertificate(
        organisation_id=org_id,
        enrollment_id=enrollment.id,
        certificate_number=next_certificate_number(session, org_id),
        verification_reference=verification_ref(),
        learner_name=learner.display_name or learner.email,
        course_title=course.title,
        provider_name=provider_name,
        status="valid",
        expires_at=expires,
    )
    session.add(cert)
    session.flush()
    return cert
