"""Deterministic housing application checklist evaluation. No housing decisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.document_checks import DocumentCheck
from app.db.models.evidence import EvidenceChecklistItem, EvidenceItemFile
from app.db.models.housing import HousingApplication, WaitingListEntry


def source_fingerprint(material: dict[str, Any]) -> str:
    encoded = json.dumps(material, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]


def _finding(
    *,
    code: str,
    source: str,
    outcome: str,
    title: str,
    detail: str,
    recommended_action: str | None = None,
    related_checklist_item_id: str | None = None,
    related_file_id: str | None = None,
    needs_human: bool = False,
) -> dict[str, Any]:
    return {
        "code": code,
        "source": source,
        "outcome": outcome,
        "title": title,
        "detail": detail,
        "recommended_action": recommended_action,
        "related_checklist_item_id": related_checklist_item_id,
        "related_file_id": related_file_id,
        "needs_human_verification": needs_human,
    }


def map_evidence_status(status: str, *, file_count: int, is_required: bool) -> tuple[str, str]:
    if status == "accepted":
        return "complete", "Checklist item is marked accepted."
    if status == "not_applicable":
        return "not_applicable", "Checklist item is marked not applicable."
    if status == "missing":
        return "missing", "Checklist item is marked missing."
    if status == "rejected":
        return "incomplete", "Checklist item was rejected and needs replacement evidence."
    if status in {"received", "under_review"}:
        return "needs_review", "Evidence is recorded and still needs staff review."
    if status == "pending":
        if file_count == 0:
            return ("missing" if is_required else "incomplete", "No evidence file is associated yet.")
        return "needs_review", "A file is associated but the checklist item is still pending review."
    return "needs_review", f"Checklist status '{status}' needs staff review."


def evaluate_application(
    session: Session,
    *,
    application: HousingApplication,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = [
        {
            "type": "housing_application",
            "id": str(application.id),
            "updated_at": application.updated_at.isoformat() if application.updated_at else None,
            "status": application.status,
        }
    ]

    if (application.housing_requirements or "").strip():
        findings.append(
            _finding(
                code="housing_requirements_present",
                source="rule",
                outcome="complete",
                title="Housing requirements recorded",
                detail="The application has housing requirements text.",
            )
        )
    else:
        findings.append(
            _finding(
                code="housing_requirements_missing",
                source="rule",
                outcome="missing",
                title="Housing requirements missing",
                detail="The application has no housing requirements text.",
                recommended_action="Ask the applicant or worker to record housing requirements.",
                needs_human=True,
            )
        )

    if (application.household_summary or "").strip():
        findings.append(
            _finding(
                code="household_summary_present",
                source="rule",
                outcome="complete",
                title="Household summary recorded",
                detail="A household summary is stored on the application.",
            )
        )
    else:
        findings.append(
            _finding(
                code="household_summary_blank",
                source="rule",
                outcome="incomplete",
                title="Household summary not recorded",
                detail="No household summary is stored. This is not a legal determination.",
                recommended_action="Confirm whether a household summary is needed for this organisation workflow.",
                needs_human=True,
            )
        )

    if not (application.supporting_information or "").strip():
        findings.append(
            _finding(
                code="supporting_information_blank",
                source="rule",
                outcome="incomplete",
                title="Supporting information not recorded",
                detail="No supporting information text is stored on the application.",
                recommended_action="Collect supporting notes if the organisation workflow expects them.",
                needs_human=True,
            )
        )

    items = list(
        session.scalars(
            select(EvidenceChecklistItem)
            .where(
                EvidenceChecklistItem.organisation_id == application.organisation_id,
                EvidenceChecklistItem.application_id == application.id,
            )
            .order_by(EvidenceChecklistItem.sort_order.asc())
        )
    )
    if not items:
        findings.append(
            _finding(
                code="checklist_not_configured",
                source="rule",
                outcome="not_performed",
                title="No evidence checklist items on this application",
                detail=(
                    "No organisation checklist items are linked to this application. "
                    "Requirements were not invented."
                ),
                recommended_action="Seed or create evidence checklist items before treating evidence as complete.",
                needs_human=True,
            )
        )
    for item in items:
        file_ids = list(
            session.scalars(
                select(EvidenceItemFile.file_id).where(EvidenceItemFile.checklist_item_id == item.id)
            )
        )
        sources.append(
            {
                "type": "evidence_checklist_item",
                "id": str(item.id),
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "status": item.status,
                "file_ids": [str(fid) for fid in file_ids],
            }
        )
        outcome, detail = map_evidence_status(item.status, file_count=len(file_ids), is_required=item.is_required)
        findings.append(
            _finding(
                code=f"evidence_{item.status}",
                source="evidence",
                outcome=outcome,
                title=item.title,
                detail=detail,
                recommended_action=(
                    None
                    if outcome in {"complete", "not_applicable"}
                    else "Collect or review evidence through the existing checklist workflow."
                ),
                related_checklist_item_id=str(item.id),
                related_file_id=str(file_ids[0]) if file_ids else None,
                needs_human=outcome in {"missing", "incomplete", "needs_review"},
            )
        )
        for file_id in file_ids:
            check = session.scalars(
                select(DocumentCheck)
                .where(
                    DocumentCheck.organisation_id == application.organisation_id,
                    DocumentCheck.file_id == file_id,
                )
                .order_by(DocumentCheck.created_at.desc())
            ).first()
            if check is None:
                findings.append(
                    _finding(
                        code="document_content_not_checked",
                        source="document",
                        outcome="not_performed",
                        title=f"Document content not checked for {item.title}",
                        detail=(
                            "A file is associated. Content was not verified here; only metadata was considered. "
                            "Use the Smart Document Checker if text extraction is needed."
                        ),
                        related_checklist_item_id=str(item.id),
                        related_file_id=str(file_id),
                        needs_human=True,
                    )
                )
                continue
            sources.append(
                {
                    "type": "document_check",
                    "id": str(check.id),
                    "updated_at": check.created_at.isoformat() if check.created_at else None,
                    "extraction_status": check.extraction_status,
                }
            )
            if check.extraction_status in {"failed", "empty", "ocr_unavailable", "unsupported"}:
                findings.append(
                    _finding(
                        code="document_extraction_issue",
                        source="document",
                        outcome="needs_review",
                        title=f"Document extraction issue for {item.title}",
                        detail=f"Existing document check extraction status is {check.extraction_status}.",
                        recommended_action="Review the document through the existing document checker and evidence workflow.",
                        related_checklist_item_id=str(item.id),
                        related_file_id=str(file_id),
                        needs_human=True,
                    )
                )

    waiting = session.scalar(
        select(WaitingListEntry).where(
            WaitingListEntry.organisation_id == application.organisation_id,
            WaitingListEntry.application_id == application.id,
        )
    )
    if waiting is not None:
        sources.append(
            {
                "type": "waiting_list_entry",
                "id": str(waiting.id),
                "updated_at": waiting.updated_at.isoformat() if waiting.updated_at else None,
                "position": waiting.position,
                "status": waiting.status,
            }
        )

    counts = {
        "complete": sum(1 for item in findings if item["outcome"] == "complete"),
        "missing": sum(1 for item in findings if item["outcome"] == "missing"),
        "incomplete": sum(1 for item in findings if item["outcome"] == "incomplete"),
        "needs_review": sum(1 for item in findings if item["outcome"] == "needs_review"),
        "not_applicable": sum(1 for item in findings if item["outcome"] == "not_applicable"),
        "not_performed": sum(1 for item in findings if item["outcome"] == "not_performed"),
    }
    fingerprint_material = {
        "application_id": str(application.id),
        "application_updated_at": application.updated_at.isoformat() if application.updated_at else None,
        "application_status": application.status,
        "housing_requirements": bool((application.housing_requirements or "").strip()),
        "household_summary": bool((application.household_summary or "").strip()),
        "supporting_information": bool((application.supporting_information or "").strip()),
        "checklist": [
            {
                "id": str(item.id),
                "status": item.status,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "files": [
                    str(fid)
                    for fid in session.scalars(
                        select(EvidenceItemFile.file_id).where(EvidenceItemFile.checklist_item_id == item.id)
                    )
                ],
            }
            for item in items
        ],
    }
    return {
        "findings": findings,
        "counts": counts,
        "sources": sources,
        "source_fingerprint": source_fingerprint(fingerprint_material),
        "application_status_unchanged": application.status,
        "legal_certification": False,
        "housing_decision": False,
    }


def heuristic_gap_narrative(findings: list[dict[str, Any]], *, application_reference: str) -> str:
    missing = [item["title"] for item in findings if item["outcome"] == "missing"]
    incomplete = [item["title"] for item in findings if item["outcome"] == "incomplete"]
    needs_review = [item["title"] for item in findings if item["outcome"] == "needs_review"]
    complete = [item["title"] for item in findings if item["outcome"] == "complete"]
    not_performed = [item["title"] for item in findings if item["outcome"] == "not_performed"]
    lines = [
        f"AI assistance only for application {application_reference}. "
        "This analysis does not determine housing eligibility, allocation, approval, or rejection.",
        f"Complete items: {len(complete)}. Missing: {len(missing)}. Incomplete: {len(incomplete)}. "
        f"Needs review: {len(needs_review)}. Not performed: {len(not_performed)}.",
    ]
    if missing:
        lines.append("Missing: " + "; ".join(missing[:8]) + ".")
    if incomplete:
        lines.append("Incomplete: " + "; ".join(incomplete[:8]) + ".")
    if needs_review:
        lines.append("Needs staff review: " + "; ".join(needs_review[:8]) + ".")
    if not_performed:
        lines.append("Could not be verified from configured rules: " + "; ".join(not_performed[:8]) + ".")
    if not missing and not incomplete and not needs_review and not not_performed:
        lines.append("No gaps were identified from the configured checklist and recorded application fields.")
    lines.append("Final decisions remain with authorised human staff through existing housing workflows.")
    return " ".join(lines)


def validate_ai_narrative(text: str) -> str:
    lowered = text.lower()
    banned = (
        "application is approved",
        "application is rejected",
        "eligible for housing",
        "not eligible",
        "allocate",
        "allocated",
        "waiting list position",
    )
    if any(token in lowered for token in banned):
        raise ValueError("AI narrative states a housing decision")
    cleaned = text.strip()
    if len(cleaned) < 20:
        raise ValueError("AI narrative is too short")
    return cleaned[:4000]
