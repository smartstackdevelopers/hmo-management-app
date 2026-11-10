# Push notification setup (F4.3)

Push extends the communication outbox. Inbox messages still work when push is unconfigured. Do not put an Expo access token, Auth0 secret, or EAS token in git.

## API

Copy the commented lines into `apps/api/.env` (and the repo-root `.env` if that is what the process loads). Leave them commented until you have a real token.

```bash
# EXPO_ACCESS_TOKEN=
# PUSH_ADAPTER_MODE=log
```

| Variable | Default | Effect |
| --- | --- | --- |
| `PUSH_ADAPTER_MODE` | `log` | `log` records `provider_not_configured` and does not call Expo. `expo` calls the Expo Push API. |
| `EXPO_ACCESS_TOKEN` | empty | Bearer token for `https://exp.host/--/api/v2/push/send`. If it is empty, even `expo` mode does not mark a delivery sent. |

Create the token in the Expo dashboard for the project that owns the app. Enhanced security for push requires this token. Store it in the API environment or a secret manager, not in the mobile app and not in a commit.

Apply the migration `20261110_3000_f43` with the API’s usual Alembic upgrade. It revises `20261110_2900_f41` and adds `push_device_tokens` plus `allow_push`.

## Worker

From `apps/api`, with `REDIS_URL` pointing at Redis:

```bash
celery -A app.workers.celery_app.celery_app worker -l info
celery -A app.workers.celery_app.celery_app beat -l info
```

Beat enqueues `hmore.push.dispatch_pending` every 45 seconds. Sending one known delivery id is `hmore.push.dispatch_delivery`. A row that is already `sent` or `failed` is left unchanged.

Until mode is `expo` and `EXPO_ACCESS_TOKEN` is set, queued push rows end as `failed` with `provider_not_configured`. That is expected. It is not a device delivery.

## Mobile

The Expo app is `room-ready`. Add a real EAS project UUID to `room-ready/.env`:

```bash
# EXPO_PUBLIC_EAS_PROJECT_ID=
```

`app.json` currently has `extra.eas.projectId` set to `room-ready-hmo`. That value is not a UUID, so the app will not call `getExpoPushTokenAsync` with it. Expo Go cannot register a production push token for this project. Use a development build or an EAS build after `eas init` has written a real project id.

`expo-notifications` is configured with Android `POST_NOTIFICATIONS`, iOS `UIBackgroundModes` `remote-notification`, and plugin `mode` `production` (APNs production). A local debug build that must use the APNs sandbox should set that mode to `development` before prebuild. The permission prompt explains that the notification does not include case or medical details.

After Auth0 sign-in and a successful HMore session, the app registers the token at `POST /api/v1/push/devices`. Sign-out calls `DELETE /api/v1/push/devices/{id}` for the stored device. The account and accessibility screens toggle `allow_push` through `GET/PATCH /api/v1/communications/preferences`.

## Honest limits

- No Android or iOS handset delivery was verified in this change. There is no Expo credential in the repo.
- An Expo ticket status of `ok` means Expo accepted the message. The API does not poll receipts and does not report that a device displayed it.
- The in-app inbox (`StaffAlertList` for staff, the tenant notifications screen for tenants) remains the record of the message.
- F4.4 and later are not part of this setup.
