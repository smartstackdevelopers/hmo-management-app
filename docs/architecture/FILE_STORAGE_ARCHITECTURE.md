# F1.8 Private File Storage Architecture

S3-compatible private object storage with organisation-scoped metadata in PostgreSQL.

## Design

| Layer | Responsibility |
| --- | --- |
| `app.storage.protocol.StorageBackend` | Provider-agnostic put/get/delete/exists |
| `memory` / `local` / `s3` adapters | Provider-specific I/O |
| `app.storage.service` | Authz context, validation, metadata, audit |
| `file_metadata` table | Metadata only — **no file bytes in Postgres** |
| `GET/POST/DELETE /api/v1/files` | Authenticated org-scoped API |

Application services must not import `boto3` directly.

## Providers

| `STORAGE_PROVIDER` | Use |
| --- | --- |
| `memory` (default) | Unit tests / local without credentials |
| `local` | Dev disk under `STORAGE_LOCAL_ROOT` (not HTTP-public) |
| `s3` | AWS S3 or MinIO / other S3-compatible **private** bucket |

## Object keys

Format: `org/{organisation_id}/{uuid}{safe_ext}`

- Never use the client filename as the key.
- Path traversal in filenames is stripped (`normalize_filename`).
- Collisions raise conflict; keys are UUID-based.

## Access model

- Upload/delete: `files.manage` (Super Admin, Organisation Admin).
- Read/download: `files.read` (same roles in Phase 1).
- Organisation ID always from trusted `OrganisationContext` + RLS on `file_metadata`.
- Downloads stream through the API (`/files/{id}/content`). No public bucket URLs. No client-supplied object keys.
- API responses never include `storage_key` or credentials.

Tenant `documents.read.own` remains reserved for future own-document linking; it does **not** grant org file library access in F1.8.

## Validation

- Configurable max size (`STORAGE_MAX_UPLOAD_BYTES`, default 10 MiB).
- Allow-list of content types.
- Magic-byte sniffing for PDF/PNG/JPEG/WEBP; extension alone is insufficient.
- Soft-delete: `status=deleted` + best-effort object delete.

## Audit events

`file.upload`, `file.upload.failure`, `file.upload.rejected`, `file.download`, `file.download.failure`, `file.delete`, `file.delete.failure` via F1.7 `record_event`. Metadata excludes file bytes, keys, and signed URLs.

## Malware scanning

**Not implemented in F1.8.** Do not claim uploads are malware-scanned. Future dependency: AV/scanning pipeline before marking files trusted for high-risk workflows.

## Production notes

- Use a private bucket with Block Public Access.
- Prefer IAM roles over long-lived keys where possible (F1.11/AWS baseline).
- TLS in transit; bucket encryption at rest (provider-side).
- Retention/deletion policy is a product decision (same posture as audit retention).
