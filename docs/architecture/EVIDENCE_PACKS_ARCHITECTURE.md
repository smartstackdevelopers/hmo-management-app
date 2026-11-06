# Evidence Checklist, Packs & Council-Ready Exports (F2.6)

## Scope

Structured evidence checklists linked to F2.5 housing applications, review workflow, private file association via F1.8, and PDF evidence pack generation for operational / council review.

**Not in scope:** statutory evidence mandates, council-certified forms, F2.7+, AI evidence decisions, public file sharing.

## Checklist model

- Organisation-scoped **templates** (`evidence_checklist_templates`) are configurable defaults. Seeded defaults are labelled as non-statutory.
- Per-application **items** (`evidence_checklist_items`) hold status, notes, dates, reviewer, and optional template link.
- Multiple private files may be linked via `evidence_item_files` → F1.8 `file_metadata`.
- Status history is append-only in `evidence_review_history`.

## Statuses and transitions

`pending → received | missing | not_applicable | under_review`

`received → under_review | accepted | rejected | missing`

`under_review → accepted | rejected | missing | received`

`accepted → under_review` (re-open)

`rejected → received | under_review | missing`

`missing → received | not_applicable | under_review`

`not_applicable → pending`

Uploading/associating a file does **not** auto-accept evidence. Rejection requires `rejection_reason`.

## Private storage

- Uploads use F1.8 `storage.service.upload_file` (validation, org-scoped keys, no public URLs).
- Evidence upload endpoint `/evidence-items/{id}/upload` allows manage roles without broad `files.manage` (support workers).
- Pack PDFs are stored as private files with `resource_type=evidence_pack`.
- Downloads go through authenticated API (`/evidence-packs/{id}/download` or `/files/{id}/content`).

## Pack generation

1. Readiness check: required items must be `accepted` or `not_applicable`.
2. Incomplete packs are blocked unless `allow_incomplete=true` (stored as `incomplete_draft` with outstanding summary).
3. PDF is a simple structured export (application reference, checklist statuses, outstanding markers). It is **not** a certified council form.

## Permissions

| Role | Access |
| --- | --- |
| Organisation Admin | Manage, review, generate packs |
| Support Worker | Manage/read assigned application evidence; `files.read` for linked downloads |
| Tenant | Read own application evidence |
| Landlord / Maintenance | Denied by default |

Organisation isolation: application tenancy + RLS on all `evidence_*` tables. Org ID from request body is never trusted.

## APIs

- `/api/v1/evidence-templates`
- `/api/v1/housing-applications/{id}/evidence` (+ `/seed`, `/readiness`, `/packs`)
- `/api/v1/evidence-items/{id}` (+ `/files`, `/upload`, `/history`)
- `/api/v1/evidence-packs/{id}` (+ `/download`)

## Migration

`20261106_1700_f26` — evidence tables + RLS policies.
