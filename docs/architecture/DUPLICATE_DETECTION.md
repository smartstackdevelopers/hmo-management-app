# F3.11 — Duplicate Detection via Search

## Overview

Identifies **potential** duplicate records using organisation-scoped database search, normalisation, and deterministic matching. Results require human review.

This feature:

- Does **not** call an AI model for every record (or for routine detection at all).
- Does **not** prove identity from similar names or shared contact details.
- Does **not** automatically delete, merge, or modify source records.
- Does **not** change tenant or application ownership.

## Supported record types

| Type | Matching signals |
| --- | --- |
| `tenant` | Normalised email, phone, tenancy reference; name similarity (possible only when alone) |
| `housing_application` | Multiple open applications sharing the same `tenant_id` |
| `file_metadata` | Exact SHA-256 checksum on active files; optional matching filename as supporting signal |

No new business record types are invented.

## Normalisation

- Trim and collapse whitespace.
- Case-fold emails, names, and references.
- Strip combining marks from names; remove punctuation for name/reference comparison without destroying identifier meaning for phones (digits retained).
- Null/missing fields are skipped safely.
- Original stored values are never overwritten by detection.

## Similarity methodology

- Tenant names use `difflib.SequenceMatcher` ratio against a configured threshold (`0.88`).
- Similarity scores are **matching-strength indicators**, not confidence that two people are the same.
- Name-only hits are always `match_strength=possible`.
- Exact normalised email or tenancy reference → `exact`.
- Phone + strong name similarity → `strong`; phone alone → `possible`.

## Candidate generation

1. Restrict to the caller’s organisation (RLS + application checks).
2. Filter with indexed fields (email lower, preferred_name lower, checksum, housing tenant/status).
3. Compare candidate pairs only (not full Cartesian product of the organisation).
4. Deduplicate pairs; skip previously dismissed (`not_duplicate`) pairs.
5. Cap pair counts and paginate listing APIs.

## Human review workflow

Authorised staff can confirm duplicate, mark not duplicate, or defer, with optional comments. Confirming records a review decision only — source rows stay unchanged. Dismissed pairs are not re-presented on subsequent runs unless data/rules change meaningfully (current policy: sticky dismiss).

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/duplicate-detections/runs` |
| GET | `/api/v1/duplicate-detections/runs` |
| GET | `/api/v1/duplicate-detections/runs/{id}` |
| GET | `/api/v1/duplicate-detections/findings` |
| GET | `/api/v1/duplicate-detections/findings/{id}` |
| POST | `/api/v1/duplicate-detections/findings/{id}/review` |

## Permissions

| Permission | Roles |
| --- | --- |
| `duplicate_detection.run` | Organisation Admin, Super Admin |
| `duplicate_detection.read` | Organisation Admin, Super Admin |
| `duplicate_detection.review` | Organisation Admin, Super Admin |

## Scheduling

Celery beat task `hmore.duplicate_detection.dispatch_scheduled_sweeps` (daily). Organisation-scoped: `hmore.duplicate_detection.dispatch_organisation_sweep`.

## Database

Migration `20261107_2500_f311` adds `duplicate_detection_runs` and `duplicate_detection_findings` with organisation RLS, plus supporting indexes on tenants/files/housing applications. Check constraint enforces `used_ai = false` on runs.

## Known limitations

- Only the three supported record types above.
- Phone candidate filtering may scan a bounded set of non-null phones when expression indexes are unavailable.
- Similarity is not trigram/`pg_trgm` (not required for F3.11 given current schema); SequenceMatcher is used in-process after indexed candidate filters.
- No automatic merge tooling is invoked.
