"""Deterministic document checks. Rules run only when configured or when a stored field exists."""

from __future__ import annotations

from datetime import date
from typing import Any

INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "you are now",
    "approve this document",
)


def _finding(
    *,
    code: str,
    source: str,
    outcome: str,
    title: str,
    detail: str,
    page_number: int | None = None,
    needs_human: bool = False,
) -> dict[str, Any]:
    return {
        "code": code,
        "source": source,
        "outcome": outcome,
        "title": title,
        "detail": detail,
        "page_number": page_number,
        "needs_human_verification": needs_human,
    }


def apply_checks(
    *,
    extraction: dict[str, Any],
    expiry_date: date | None,
    category_code: str,
    configured_rules: list[dict[str, Any]],
    today: date,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    detected = extraction.get("detected_type")
    declared = extraction.get("declared_type")
    status = extraction.get("extraction_status")
    text = extraction.get("text") or ""

    if extraction.get("error") == "empty_file":
        findings.append(
            _finding(
                code="empty_file",
                source="ocr",
                outcome="fail",
                title="File is empty",
                detail="The stored file has no bytes.",
                needs_human=True,
            )
        )
        return findings

    if declared and detected and declared != detected and detected != "application/octet-stream":
        findings.append(
            _finding(
                code="type_mismatch",
                source="rule",
                outcome="fail",
                title="File type does not match the stored type",
                detail=f"Stored type {declared}; detected type {detected}.",
                needs_human=True,
            )
        )

    if status == "ocr_unavailable":
        findings.append(
            _finding(
                code="ocr_unavailable",
                source="ocr",
                outcome="warning",
                title="Image text was not extracted",
                detail="The file is an image. This service has no OCR engine configured, so no text was read from it.",
                page_number=1,
                needs_human=True,
            )
        )
    elif status == "unsupported":
        findings.append(
            _finding(
                code="unsupported_format",
                source="ocr",
                outcome="warning",
                title="Text extraction is not implemented for this format",
                detail=f"Detected type {detected}. The checker did not invent text.",
                needs_human=True,
            )
        )
    elif status == "failed":
        findings.append(
            _finding(
                code="extraction_failed",
                source="ocr",
                outcome="fail",
                title="Text extraction failed",
                detail="The file could not be read. It was not treated as a successful extraction.",
                needs_human=True,
            )
        )
    elif status == "empty":
        findings.append(
            _finding(
                code="no_embedded_text",
                source="ocr",
                outcome="fail",
                title="No embedded text found",
                detail="The PDF or text file produced no readable text.",
                needs_human=True,
            )
        )
    elif status == "partial":
        findings.append(
            _finding(
                code="partial_text",
                source="ocr",
                outcome="warning",
                title="Only a short text extract was found",
                detail="Extracted text is very short. A person should check whether pages are missing or unreadable.",
                page_number=1,
                needs_human=True,
            )
        )
    else:
        findings.append(
            _finding(
                code="text_extracted",
                source="ocr",
                outcome="pass",
                title="Embedded text extracted",
                detail="Text was read from the file. This is not a statement that the document is valid.",
            )
        )

    lowered = text.lower()
    if any(marker in lowered for marker in INJECTION_MARKERS):
        findings.append(
            _finding(
                code="untrusted_instruction",
                source="ocr",
                outcome="warning",
                title="Extracted text contains instruction-like wording",
                detail="Document text is untrusted data. It cannot change permissions, approve the document, or override checks.",
                needs_human=True,
            )
        )

    applicable = [
        rule
        for rule in configured_rules
        if rule.get("enabled", True)
        and rule.get("category_code") in {"", category_code}
    ]
    if not applicable:
        findings.append(
            _finding(
                code="no_configured_rules",
                source="rule",
                outcome="not_performed",
                title="No validation rules configured",
                detail="No organisation rule applies to this category. The document was not marked invalid.",
            )
        )
    for rule in applicable:
        kind = rule.get("rule_kind")
        if kind == "require_extracted_text":
            ok = status == "extracted" and bool(text.strip())
            findings.append(
                _finding(
                    code="require_extracted_text",
                    source="rule",
                    outcome="pass" if ok else "fail",
                    title="Required extracted text",
                    detail="Configured rule: the file must contain extracted text."
                    if ok
                    else "Configured rule failed: no usable extracted text.",
                    needs_human=not ok,
                )
            )
        elif kind == "require_expiry_date":
            ok = expiry_date is not None
            findings.append(
                _finding(
                    code="require_expiry_date",
                    source="rule",
                    outcome="pass" if ok else "fail",
                    title="Expiry date recorded",
                    detail="An expiry date is stored on the document."
                    if ok
                    else "Configured rule: this category requires an expiry date on the document record. None is stored.",
                    needs_human=not ok,
                )
            )
        elif kind == "expiry_not_past":
            if expiry_date is None:
                findings.append(
                    _finding(
                        code="expiry_not_past",
                        source="rule",
                        outcome="not_performed",
                        title="Expiry date was not checked",
                        detail="The configured expiry rule did not run because no expiry date is stored.",
                    )
                )
            else:
                ok = expiry_date >= today
                findings.append(
                    _finding(
                        code="expiry_not_past",
                        source="rule",
                        outcome="pass" if ok else "fail",
                        title="Stored expiry date",
                        detail=f"Stored expiry date {expiry_date.isoformat()} is not before {today.isoformat()}."
                        if ok
                        else f"Stored expiry date {expiry_date.isoformat()} is before {today.isoformat()}.",
                        needs_human=not ok,
                    )
                )
        elif kind == "require_phrase":
            phrase = (rule.get("parameter") or "").strip()
            if not phrase:
                findings.append(
                    _finding(
                        code="require_phrase",
                        source="rule",
                        outcome="not_performed",
                        title="Phrase rule has no phrase",
                        detail="The configured phrase rule has an empty parameter, so it was not applied.",
                    )
                )
            elif status not in {"extracted", "partial"}:
                findings.append(
                    _finding(
                        code="require_phrase",
                        source="rule",
                        outcome="not_performed",
                        title="Phrase rule not applied",
                        detail="There is no extracted text to compare with the configured phrase.",
                    )
                )
            else:
                ok = phrase.lower() in lowered
                findings.append(
                    _finding(
                        code="require_phrase",
                        source="rule",
                        outcome="pass" if ok else "fail",
                        title="Configured phrase",
                        detail=f"The extracted text contains the configured phrase."
                        if ok
                        else "The extracted text does not contain the configured phrase. This is not a legal judgement.",
                        needs_human=not ok,
                    )
                )
    return findings


def check_status_for(findings: list[dict[str, Any]], extraction_status: str) -> str:
    if extraction_status in {"failed", "empty"}:
        return "extraction_failed"
    if any(item["outcome"] in {"fail", "warning"} for item in findings):
        return "needs_review"
    return "completed"
