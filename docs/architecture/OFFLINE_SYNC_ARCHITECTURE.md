# Offline sync architecture (F4.5)

Offline drafts stay on the device until the API confirms them. The app syncs when the user taps Sync Now, and once after connectivity returns. It does not run a continuous background sync. iOS and Android limit how long an app can work after it leaves the foreground, so a draft can sit until the next Sync Now or the next time the app sees a healthy connection.

## Drafts

`room-ready/lib/hmore/offline/store.ts` keeps a 32-byte key in SecureStore and the draft list in AsyncStorage. The list is XOR-encrypted with that key. SecureStore values are limited to about 2048 bytes, so note text and photo bytes are not written there. XOR hides the JSON from a casual read of AsyncStorage. It is not a substitute for device encryption: anyone who can read both stores can decrypt the drafts.

Each draft is bound to `user_id` and `organisation_id`. The storage key includes both. Loading another account's envelope throws, and signing in as a different account deletes the previous account's draft payload. Drafts saved before this binding, which had no owner, are removed on the next signed-in load rather than shown to that account.

A draft has `id`, `clientRequestId`, `type`, `payload`, `localAttachmentUris`, `syncState`, `lastError`, `serverUpdatedAt`, `localUpdatedAt`, and `serverResourceId`. States are `draft`, `pending`, `syncing`, `synced`, `failed`, `conflict`, and `needs_attention`. Passwords and tokens are stripped before the payload is stored.

Types are `daily_log`, `repair_create`, `visit_update`, `task_update`, and `work_order_update`. Saving the same record again keeps the same `clientRequestId`. Repair and work-order photos are copied under the app document directory at `hmore-offline/{organisation}/{user}/`. A local file is deleted only after that photo's upload returns success.

## Sync

`syncEngine.ts` sends the queue one draft at a time. The `Idempotency-Key` header is the draft's `clientRequestId`. A draft is removed only after a 2xx response. If it has photos, it stays until each remaining upload also succeeds. A network failure or 5xx marks `failed` and leaves the draft. A 409 marks `conflict`, stores the server `updated_at` when the body includes it, and does not overwrite the local payload. Other 4xx responses mark `needs_attention`. Sync Now retries `draft`, `pending`, `failed`, and interrupted `syncing` rows. It does not retry `conflict` or `needs_attention`. Retry failed sends only `failed` rows.

`network.ts` uses NetInfo and `GET /health` on the API base (`/api/v1/health`). Offline means the device reports no connection. Unstable means the device has a connection and the health check failed. Online means both succeeded. Auto-sync is a single debounced run, about 1.5 seconds after the status changes from offline or unstable to online.

The status bar is on the signed-in app shell. Staff More and the tenant Account screen open the offline drafts list.

F4.6 skips Sync Now when this device's session is revoked or reported lost. The drafts stay on the device. See `docs/architecture/BIOMETRIC_REMOTE_SIGNOUT_ARCHITECTURE.md`.

## Server

Migration `20261110_3200_f45` adds `client_idempotency_keys`, revises `20261110_3000_f43`, and keeps organisation row-level security. The unique key is `(organisation_id, user_id, scope, key)`. The first success stores `resource_type`, `resource_id`, and `response_snapshot`. A repeat of that key returns the stored status and body and does not insert another row.

The header is honoured on:

- `POST /daily-logs`
- `POST /maintenance`
- `PATCH /visits/{id}`
- `PATCH /tasks/{id}`
- `PATCH /maintenance/{id}` and `POST /maintenance/{id}/notes`
- `POST /maintenance/{id}/transition` and `POST /maintenance/{id}/complete`, so a retried work-order action does not run twice. Those bodies also accept `if_match_updated_at` and return 409 without applying the change when it does not match.

`resource_id` is empty only while that request's transaction is still open. A rollback removes the claim.

PATCH bodies may include `if_match_updated_at`. If it does not match the row's `updated_at`, the API returns 409 with `detail.code = conflict` and `detail.updated_at` set to the current value. The row is not changed. The client keeps the draft for the user to review. Visit, task, and safe work-order updates send the timestamp they last saw. Creating a daily log or a repair does not use this check.

Offline sync does not approve a request, set emergency priority, or decide an approval. Those still happen only when an authorised call reaches the server and the server accepts it. A lost response is safe to retry because the idempotency key returns the first success.

## What this does not do

There is no background upload while the app is suspended. There is no automatic merge: a conflict stays on the device. Photo upload itself is not idempotent; a photo is removed locally only after its own 2xx, so a lost upload response can upload that photo again on the next retry. This was not verified on a physical device in airplane mode.
