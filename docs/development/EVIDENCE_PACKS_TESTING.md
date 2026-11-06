# F2.6 Evidence Packs — Testing

## Backend

From `apps/api`:

```text
pytest tests/test_f26_evidence_packs.py -q
pytest tests/test_f26_evidence_packs.py -q -m postgres
```

Coverage includes:

- Permission matrix allow/deny
- Status transition rules (unit)
- PDF builder header/content (unit, no DB)
- Unauthenticated API 401 (unit)
- Checklist seed/create/update/review (postgres)
- Rejection reason validation (postgres)
- File upload association via F1.8 memory storage (mocked provider; real DB)
- Readiness / incomplete pack warning (postgres)
- Pack generate + download (postgres + memory storage)
- Audit events (postgres)
- Cross-organisation denial (postgres)
- Maintenance role denial (postgres)

Skipped postgres tests are reported as skipped when `DATABASE_URL` / test DB is unavailable — do not treat skips as passes.

## Frontend

Playwright helper checks in `apps/web/e2e/evidence.spec.ts` cover status labelling, blocking status detection, and readiness warning copy.

Manual UI checks on `/dashboard/housing-applications/[id]`:

- Checklist empty/loading/error states
- Seed / add / upload / review visibility by role
- Incomplete pack warning and confirmation before generate
- Pack history download

## Migration

```text
cd apps/api
alembic upgrade head
```

Revision: `20261106_1700_f26`.
