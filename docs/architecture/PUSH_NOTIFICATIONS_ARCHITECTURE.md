# Push notifications (F4.3)

Push is another channel on the F2.12 communication platform. It is not a second inbox.

## Flow

1. The signed-in mobile app asks for notification permission, then `POST /api/v1/push/devices` with an Expo push token. The row is stored on `push_device_tokens` for that user and organisation.
2. `send_message` still writes the inbox recipient. It also queues a `communication_deliveries` row with `channel = push` when `allow_push` is true and the recipient has an active token. Announcement publish does the same for recipients when the announcement selects `push`. Operational reminders can use channel `push` through `CommunicationNotificationProvider`; email, SMS, and in-app are unchanged.
3. Celery task `hmore.push.dispatch_delivery` sends one queued row. Beat runs `hmore.push.dispatch_pending` every 45 seconds for anything still queued.
4. A tap uses the same `staffAlertHref` links as `StaffAlertList`. Tenants open the notifications inbox, or a maintenance request when that id is present. If `message_id` is present the app marks that inbox message read.

## Delivery status

Push rows move `queued` → `sending` → `sent` or `failed`.

| Status | Meaning |
| --- | --- |
| `queued` | Outbox row created. Expo has not been called. |
| `sending` | Worker has started this attempt. A crash before commit leaves the row queued. |
| `sent` | Expo returned a ticket with status `ok` and a ticket id. This is provider acceptance, not proof a handset showed the notification. |
| `failed` | Not sent. Log mode, a missing token, an HTTP error, or an Expo error. |

`delivered` stays reserved for in-app storage. Push never uses a `device_received` status. There is no Expo receipt poll in this release, so the API cannot claim the device displayed anything.

Log mode (`PUSH_ADAPTER_MODE=log`, the default) does not call Expo. The delivery is `failed` with `provider_not_configured: not_sent_provider_unconfigured`. A configured `EXPO_ACCESS_TOKEN` is ignored until the mode is `expo`. If the mode is `expo` and the token is empty, the worker uses the same not-sent result.

`DeviceNotRegistered` or an invalid Expo token deactivates that device (`is_active` false, `disabled_reason` `DeviceNotRegistered`) and fails the delivery. A later register from the same user reactivates their own token. A token already owned by someone else is rejected with HTTP 409.

## Privacy

The Expo payload title is `HMore` and the body is a fixed sentence: a notification is waiting. `data` may contain only `message_id`, `related_resource_type`, and `related_resource_id`. Incident narrative, message text, and medical detail are not copied into the push body or data.

`allow_push` defaults to true on `communication_user_preferences`. Setting it false skips enqueue. The inbox message is still created.

## Isolation

`push_device_tokens` uses the same organisation RLS policy as other organisation tables. List and deactivate only return or change rows for the caller’s organisation and user. The Expo token itself is unique across the platform so it cannot be silently rebound to a different user.

## What is not claimed

Without an Expo access token, an EAS project id, and a development or store build, no notification is delivered to an Android or iOS device. Expo Go and the placeholder `extra.eas.projectId` in `app.json` are not enough. Ticket status `ok` is not device receipt.
