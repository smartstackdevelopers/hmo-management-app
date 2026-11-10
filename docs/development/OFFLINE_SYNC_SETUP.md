# Offline sync setup (F4.5)

From the monorepo root:

```bash
npm install
npm run typecheck -w room-ready
npm test -w room-ready
```

API unit tests, from `apps/api`:

```bash
python -m pytest tests/test_f45_offline_sync.py tests/test_f41_tenant_mobile.py::test_alembic_head_revises_f41_tenant_mobile
```

Apply migration `20261110_3200_f45` with the API's usual Alembic upgrade. It revises `20261110_3000_f43` and adds `client_idempotency_keys`. The API base URL is unchanged. The app calls `GET /health` through that base, which is `/api/v1/health`.

`room-ready` depends on `expo-file-system` so repair and work-order photos can be copied into the app documents folder. A development build is required before that native module is present. Jest covers the queue with stand-in storage and does not exercise a handset.

## What to expect

- Airplane mode, or a failed health check while the radio is up, leaves a draft on the device. The status bar says Offline or Unstable. It does not say the record was saved on the server.
- Sync Now on the offline drafts screen sends waiting and failed drafts. Retry failed sends only failed ones. A conflict stays until someone opens it.
- Coming back online queues one sync after a short delay. Leaving the app does not keep syncing.
- Signing in as someone else hides and deletes the previous account's drafts on that device. The same account keeps its drafts across a sign-out, because they are stored under that user and organisation.
- A repeated `Idempotency-Key` returns the first successful resource. A PATCH with a stale `if_match_updated_at` returns 409 and does not change the row.

See `docs/architecture/OFFLINE_SYNC_ARCHITECTURE.md`.
