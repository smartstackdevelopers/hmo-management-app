# F2.11 document management — testing

## Backend (pytest)

- **PostgreSQL required** for `@pytest.mark.postgres` cases (otherwise skipped with a clear message).
- File: `apps/api/tests/test_f211_managed_documents.py`
  - Cross-organisation denial for document reads.
  - Reminder scan idempotency + dispatch creating `ManagedDocumentReminderLog` and audit `DOCUMENT_EXPIRY_REMINDER_DISPATCHED`.
  - Signature request blocks new version until completion; after completion a new version is allowed and `current_version_id` updates.

Run from `apps/api`:

```bash
python -m pytest tests/test_f211_managed_documents.py -q
```

Full suite (when `DATABASE_URL` / `TEST_DATABASE_URL` set):

```bash
python -m pytest -q
```

## Frontend

- Typecheck: `cd apps/web && npm run typecheck`
- Navigation filter test (Playwright): `dashboard.spec.ts` includes `documents.read.meta`.

## Migrations

Revision `20261106_2200_f211` — apply via Alembic (`docs/development/DATABASE_MIGRATIONS.md`).

## Manual checks

- Upload via `POST /api/v1/documents` (multipart: `file` + `metadata` JSON).
- Download only with `documents.read.content` through `GET /api/v1/documents/{id}/content`.
- Seed categories: `POST /api/v1/documents/categories/seed-defaults` (org admin / super admin).
