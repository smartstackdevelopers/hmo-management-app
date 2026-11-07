# F3.6 — Smart Document Checker

## Overview

Checks an existing managed document. The original file and the document record are not modified.

Order of work:

1. Read the current document version from private storage.
2. Detect the file type from bytes, not from the client filename.
3. Extract embedded text from PDF and plain text.
4. Run deterministic checks.
5. Ask the shared AI service to explain gaps only when a check needs explanation and the AI service is configured.
6. A person with review permission can confirm or dismiss findings.

The result is assistance. It is not a legal certification, housing decision, or document approval.

## Supported extraction

| Detected type | What this version does |
| --- | --- |
| `application/pdf` | Reads uncompressed and FlateDecode text operators (`Tj` strings). Tested with the in-repo simple PDF builder. |
| `text/plain` | Decodes UTF-8 text. |
| `image/jpeg`, `image/png`, `image/webp` | Magic bytes are recognised. No OCR engine is installed, so status is `ocr_unavailable` and no text is invented. |
| DOCX and other Office files | Stored by the existing uploader, but text extraction is not implemented. Status `unsupported`. |

## Rules

Always-on checks use the file itself: empty, type mismatch, extraction outcome, and instruction-like wording in extracted text (treated as untrusted data).

Optional organisation rules (`POST /api/v1/document-checks/rules`):

- `require_extracted_text`
- `require_expiry_date` (uses the date already stored on the document)
- `expiry_not_past` (runs only when a date is stored; otherwise `not_performed`)
- `require_phrase` (a phrase the organisation configured)

If no rule is configured, the checker says so. It does not mark the document invalid for a missing legal rule that was never configured.

## AI

Feature id: `ai.workflow.document_checker`. Workflow: `document_check`.

The model receives finding codes and a short excerpt, not the original file. Observations must cite a finding code. Text that approves the document or states eligibility is rejected. A usage-cap response (HTTP 402) keeps the rule results and sets `ai_status=skipped_budget`. If the AI service URL is unset outside production, explanations are a local restatement of findings (`ai_status=heuristic`).

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/document-checks` `{ document_id, force }` |
| GET | `/api/v1/document-checks/documents/{document_id}` |
| GET | `/api/v1/document-checks/{id}` |
| GET | `/api/v1/document-checks/{id}/text` |
| POST | `/api/v1/document-checks/{id}/review` |
| POST | `/api/v1/document-checks/findings/{id}/decide` `{ decision: confirm\|dismiss }` |
| POST | `/api/v1/document-checks/rules` |

Same document version, checksum, and checker version returns the existing result unless `force=true`. A new document version gets its own result.

## Permissions

| Permission | Roles |
| --- | --- |
| `ai.document_check.run` | Support Worker, Organisation Admin, Super Admin |
| `ai.document_check.read` | Support Worker, Organisation Admin, Super Admin |
| `ai.document_check.review` | Organisation Admin, Super Admin |

Run also requires permission to read document content. Visibility uses the existing document access rules.

## Database

Migration `20261107_1800_f36` adds `document_check_rules`, `document_checks`, `document_check_findings`, and `document_check_observations`, each with organisation row-level security.

## Status values

`processing`, `completed`, `needs_review`, `extraction_failed`, `processing_failed`.

None of these means the document is officially valid.

## Known limitations

- Image OCR is not implemented. There is no Tesseract or external OCR service in this deployment.
- PDF extraction covers embedded text operators, not scanned pages inside a PDF.
- Checks run in the API request, within the existing upload size limit. A separate worker is not required for this version.
- Approval of a finding does not change document status, housing, or eligibility.
