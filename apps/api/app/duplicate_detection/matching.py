"""Deterministic candidate matching for tenants, housing applications, and files.

Similarity scores are matching-strength indicators, not identity proof.
Name-only similarity never yields an exact/strong match by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.enums import RecordStatus
from app.db.models.file_metadata import FileMetadata
from app.db.models.housing import HousingApplication
from app.db.models.tenant import Tenant
from app.duplicate_detection.normalize import (
    name_prefix,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_reference,
)

OPEN_APPLICATION_STATUSES = frozenset(
    {"draft", "submitted", "under_review", "information_required", "approved"}
)

NAME_SIMILARITY_THRESHOLD = 0.88


@dataclass
class MatchHit:
    record_type: str
    source_id: UUID
    candidate_id: UUID
    match_strength: str
    similarity_score: float | None
    matching_fields: list[str] = field(default_factory=list)
    matching_reasons: list[str] = field(default_factory=list)

    def ordered_ids(self) -> tuple[UUID, UUID]:
        return (self.source_id, self.candidate_id) if self.source_id.hex < self.candidate_id.hex else (
            self.candidate_id,
            self.source_id,
        )

    def dedupe_key(self) -> str:
        left, right = self.ordered_ids()
        return f"{self.record_type}:{left}:{right}"


def _name_similarity(a: str | None, b: str | None) -> float | None:
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return None
    return SequenceMatcher(None, na, nb).ratio()


def _pair_key(a: UUID, b: UUID) -> tuple[UUID, UUID]:
    return (a, b) if a.hex < b.hex else (b, a)


def detect_tenant_duplicates(
    session: Session,
    organisation_id: UUID,
    *,
    source_id: UUID | None = None,
    limit_pairs: int = 200,
) -> tuple[int, int, list[MatchHit]]:
    stmt = select(Tenant).where(
        Tenant.organisation_id == organisation_id,
        Tenant.status != RecordStatus.ARCHIVED,
    )
    if source_id is not None:
        source = session.get(Tenant, source_id)
        if source is None or source.organisation_id != organisation_id:
            return 0, 0, []
        rows = [source]
        # Candidate pool: same email/phone/reference/prefix — indexed filters.
        candidates: list[Tenant] = []
        email = normalize_email(source.email)
        phone = normalize_phone(source.phone)
        ref = normalize_reference(source.tenancy_reference)
        prefix = name_prefix(source.preferred_name or source.full_name)
        seen: set[UUID] = {source.id}
        if email:
            for row in session.scalars(
                select(Tenant).where(
                    Tenant.organisation_id == organisation_id,
                    Tenant.status != RecordStatus.ARCHIVED,
                    func.lower(Tenant.email) == email,
                    Tenant.id != source.id,
                ).limit(50)
            ):
                if row.id not in seen:
                    candidates.append(row)
                    seen.add(row.id)
        if phone:
            # Phone stored variously; filter by trailing digits using Python after limited fetch.
            phone_rows = list(
                session.scalars(
                    select(Tenant).where(
                        Tenant.organisation_id == organisation_id,
                        Tenant.status != RecordStatus.ARCHIVED,
                        Tenant.phone.is_not(None),
                        Tenant.id != source.id,
                    ).limit(500)
                )
            )
            for row in phone_rows:
                if normalize_phone(row.phone) == phone and row.id not in seen:
                    candidates.append(row)
                    seen.add(row.id)
        if ref:
            for row in session.scalars(
                select(Tenant).where(
                    Tenant.organisation_id == organisation_id,
                    Tenant.status != RecordStatus.ARCHIVED,
                    Tenant.tenancy_reference.is_not(None),
                    Tenant.id != source.id,
                ).limit(200)
            ):
                if normalize_reference(row.tenancy_reference) == ref and row.id not in seen:
                    candidates.append(row)
                    seen.add(row.id)
        if prefix:
            for row in session.scalars(
                select(Tenant).where(
                    Tenant.organisation_id == organisation_id,
                    Tenant.status != RecordStatus.ARCHIVED,
                    func.lower(Tenant.preferred_name).like(f"{prefix}%"),
                    Tenant.id != source.id,
                ).limit(100)
            ):
                if row.id not in seen:
                    candidates.append(row)
                    seen.add(row.id)
        compare_pairs = [(source, other) for other in candidates]
        scanned = 1 + len(candidates)
    else:
        rows = list(session.scalars(stmt.limit(2000)))
        scanned = len(rows)
        by_email: dict[str, list[Tenant]] = {}
        by_phone: dict[str, list[Tenant]] = {}
        by_ref: dict[str, list[Tenant]] = {}
        by_prefix: dict[str, list[Tenant]] = {}
        for row in rows:
            email = normalize_email(row.email)
            phone = normalize_phone(row.phone)
            ref = normalize_reference(row.tenancy_reference)
            prefix = name_prefix(row.preferred_name or row.full_name)
            if email:
                by_email.setdefault(email, []).append(row)
            if phone:
                by_phone.setdefault(phone, []).append(row)
            if ref:
                by_ref.setdefault(ref, []).append(row)
            if prefix:
                by_prefix.setdefault(prefix, []).append(row)
        compare_pairs = []
        seen_pairs: set[tuple[UUID, UUID]] = set()

        def add_group(group: list[Tenant]) -> None:
            for i, left in enumerate(group):
                for right in group[i + 1 :]:
                    key = _pair_key(left.id, right.id)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    compare_pairs.append((left, right))

        for group in by_email.values():
            if len(group) > 1:
                add_group(group)
        for group in by_phone.values():
            if len(group) > 1:
                add_group(group)
        for group in by_ref.values():
            if len(group) > 1:
                add_group(group)
        for group in by_prefix.values():
            if len(group) > 1:
                add_group(group[:20])

    hits: list[MatchHit] = []
    compared = 0
    for left, right in compare_pairs:
        compared += 1
        fields: list[str] = []
        reasons: list[str] = []
        score_bits: list[float] = []
        email_match = (
            normalize_email(left.email)
            and normalize_email(left.email) == normalize_email(right.email)
        )
        phone_match = (
            normalize_phone(left.phone)
            and normalize_phone(left.phone) == normalize_phone(right.phone)
        )
        ref_match = (
            normalize_reference(left.tenancy_reference)
            and normalize_reference(left.tenancy_reference)
            == normalize_reference(right.tenancy_reference)
        )
        name_score = _name_similarity(left.preferred_name or left.full_name, right.preferred_name or right.full_name)
        if email_match:
            fields.append("email")
            reasons.append("Exact normalised email match")
            score_bits.append(1.0)
        if phone_match:
            fields.append("phone")
            reasons.append("Exact normalised telephone match")
            score_bits.append(1.0)
        if ref_match:
            fields.append("tenancy_reference")
            reasons.append("Exact normalised tenancy reference match")
            score_bits.append(1.0)
        if name_score is not None and name_score >= NAME_SIMILARITY_THRESHOLD:
            fields.append("preferred_name")
            reasons.append(
                f"Similar normalised name (ratio {name_score:.2f}; not identity proof alone)"
            )
            score_bits.append(name_score)
        if not fields:
            continue
        # Name-only similarity is never exact/strong — different people can share names.
        if email_match or ref_match:
            strength = "exact"
        elif phone_match and name_score is not None and name_score >= NAME_SIMILARITY_THRESHOLD:
            strength = "strong"
        else:
            strength = "possible"
        left_id, right_id = _pair_key(left.id, right.id)
        hits.append(
            MatchHit(
                record_type="tenant",
                source_id=left_id,
                candidate_id=right_id,
                match_strength=strength,
                similarity_score=round(sum(score_bits) / len(score_bits), 4) if score_bits else None,
                matching_fields=fields,
                matching_reasons=reasons,
            )
        )
        if len(hits) >= limit_pairs:
            break
    return scanned, compared, hits


def detect_housing_application_duplicates(
    session: Session,
    organisation_id: UUID,
    *,
    source_id: UUID | None = None,
    limit_pairs: int = 200,
) -> tuple[int, int, list[MatchHit]]:
    """Open applications sharing the same tenant are potential duplicates for review."""
    stmt = select(HousingApplication).where(
        HousingApplication.organisation_id == organisation_id,
        HousingApplication.status.in_(tuple(OPEN_APPLICATION_STATUSES)),
    )
    if source_id is not None:
        source = session.get(HousingApplication, source_id)
        if source is None or source.organisation_id != organisation_id:
            return 0, 0, []
        others = list(
            session.scalars(
                stmt.where(
                    HousingApplication.tenant_id == source.tenant_id,
                    HousingApplication.id != source.id,
                ).limit(50)
            )
        )
        scanned = 1 + len(others)
        pairs = [(source, other) for other in others]
    else:
        rows = list(session.scalars(stmt.limit(2000)))
        scanned = len(rows)
        by_tenant: dict[UUID, list[HousingApplication]] = {}
        for row in rows:
            by_tenant.setdefault(row.tenant_id, []).append(row)
        pairs = []
        for group in by_tenant.values():
            if len(group) < 2:
                continue
            for i, left in enumerate(group):
                for right in group[i + 1 :]:
                    pairs.append((left, right))

    hits: list[MatchHit] = []
    compared = 0
    for left, right in pairs:
        compared += 1
        left_id, right_id = _pair_key(left.id, right.id)
        hits.append(
            MatchHit(
                record_type="housing_application",
                source_id=left_id,
                candidate_id=right_id,
                match_strength="strong",
                similarity_score=1.0,
                matching_fields=["tenant_id", "status"],
                matching_reasons=[
                    "Multiple open housing applications share the same tenant record",
                    f"Statuses: {left.status} and {right.status}",
                ],
            )
        )
        if len(hits) >= limit_pairs:
            break
    return scanned, compared, hits


def detect_file_duplicates(
    session: Session,
    organisation_id: UUID,
    *,
    source_id: UUID | None = None,
    limit_pairs: int = 200,
) -> tuple[int, int, list[MatchHit]]:
    stmt = select(FileMetadata).where(
        FileMetadata.organisation_id == organisation_id,
        FileMetadata.status == "active",
        FileMetadata.checksum_sha256.is_not(None),
    )
    if source_id is not None:
        source = session.get(FileMetadata, source_id)
        if source is None or source.organisation_id != organisation_id or not source.checksum_sha256:
            return 0, 0, []
        others = list(
            session.scalars(
                stmt.where(
                    FileMetadata.checksum_sha256 == source.checksum_sha256,
                    FileMetadata.id != source.id,
                ).limit(50)
            )
        )
        scanned = 1 + len(others)
        pairs = [(source, other) for other in others]
    else:
        rows = list(session.scalars(stmt.limit(5000)))
        scanned = len(rows)
        by_checksum: dict[str, list[FileMetadata]] = {}
        for row in rows:
            assert row.checksum_sha256 is not None
            by_checksum.setdefault(row.checksum_sha256, []).append(row)
        pairs = []
        for group in by_checksum.values():
            if len(group) < 2:
                continue
            for i, left in enumerate(group):
                for right in group[i + 1 :]:
                    pairs.append((left, right))

    hits: list[MatchHit] = []
    compared = 0
    for left, right in pairs:
        compared += 1
        left_id, right_id = _pair_key(left.id, right.id)
        reasons = ["Exact SHA-256 checksum match for active files"]
        fields = ["checksum_sha256"]
        if (
            left.original_filename
            and right.original_filename
            and left.original_filename.lower() == right.original_filename.lower()
        ):
            fields.append("original_filename")
            reasons.append("Matching original filename (supporting signal)")
        hits.append(
            MatchHit(
                record_type="file_metadata",
                source_id=left_id,
                candidate_id=right_id,
                match_strength="exact",
                similarity_score=1.0,
                matching_fields=fields,
                matching_reasons=reasons,
            )
        )
        if len(hits) >= limit_pairs:
            break
    return scanned, compared, hits


SUPPORTED_RECORD_TYPES = ("tenant", "housing_application", "file_metadata")


def run_detectors(
    session: Session,
    organisation_id: UUID,
    *,
    record_types: list[str] | None = None,
    source_record_type: str | None = None,
    source_record_id: UUID | None = None,
) -> tuple[int, int, list[MatchHit]]:
    types = record_types or list(SUPPORTED_RECORD_TYPES)
    if source_record_type:
        types = [source_record_type]
    scanned = 0
    compared = 0
    hits: list[MatchHit] = []
    for record_type in types:
        if record_type == "tenant":
            s, c, h = detect_tenant_duplicates(
                session, organisation_id, source_id=source_record_id if source_record_type == "tenant" else None
            )
        elif record_type == "housing_application":
            s, c, h = detect_housing_application_duplicates(
                session,
                organisation_id,
                source_id=source_record_id if source_record_type == "housing_application" else None,
            )
        elif record_type == "file_metadata":
            s, c, h = detect_file_duplicates(
                session,
                organisation_id,
                source_id=source_record_id if source_record_type == "file_metadata" else None,
            )
        else:
            continue
        scanned += s
        compared += c
        hits.extend(h)
    # Deduplicate hits by dedupe_key keeping strongest
    strength_rank = {"exact": 3, "strong": 2, "possible": 1}
    best: dict[str, MatchHit] = {}
    for hit in hits:
        key = hit.dedupe_key()
        existing = best.get(key)
        if existing is None or strength_rank[hit.match_strength] > strength_rank[existing.match_strength]:
            best[key] = hit
    return scanned, compared, list(best.values())


def record_summary(session: Session, record_type: str, record_id: UUID) -> dict[str, Any] | None:
    if record_type == "tenant":
        row = session.get(Tenant, record_id)
        if row is None:
            return None
        return {
            "id": str(row.id),
            "record_type": "tenant",
            "preferred_name": row.preferred_name,
            "full_name": row.full_name,
            "email": row.email,
            "phone": row.phone,
            "tenancy_reference": row.tenancy_reference,
            "status": row.status.value if hasattr(row.status, "value") else str(row.status),
        }
    if record_type == "housing_application":
        row = session.get(HousingApplication, record_id)
        if row is None:
            return None
        return {
            "id": str(row.id),
            "record_type": "housing_application",
            "reference_number": row.reference_number,
            "tenant_id": str(row.tenant_id),
            "status": row.status,
            "priority": row.priority,
        }
    if record_type == "file_metadata":
        row = session.get(FileMetadata, record_id)
        if row is None:
            return None
        return {
            "id": str(row.id),
            "record_type": "file_metadata",
            "original_filename": row.original_filename,
            "content_type": row.content_type,
            "size_bytes": row.size_bytes,
            "checksum_sha256": row.checksum_sha256,
            "status": row.status,
        }
    return None
