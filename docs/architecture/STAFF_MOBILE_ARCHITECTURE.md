# Staff mobile architecture (F4.2)

The staff mobile app is the same Expo project as the tenant app, `room-ready/`. A signed-in tenant (`active_role === 'tenant'`) keeps the F4.1 tabs. Support workers, organisation admins, and maintenance contractors get a staff shell. Super admin platform tools stay on the web dashboard.

## Roles

`mapHmoreRole` in `room-ready/lib/hmore/roles.ts` keeps `support_worker` as `support_worker`. It no longer maps that role to `property_manager`. `organisation_admin` gets the support shell plus the approvals inbox when `approvals.inbox.read` is present. `approvals.decide` is what shows the decision buttons; support workers can read the inbox and cannot decide. `maintenance_contractor` maps to the existing `contractor` role, and the HMore session switches that role onto work orders, scheduling, photos, alerts, and account. A password-login contractor without an HMore session keeps the older Jobs / Schedule / Messages tabs.

The support tab bar is Home, My Tenants, Shifts, Notes, and More. Visits, tasks, incidents, occupancy surveys, notifications, and approvals are screens opened from Home and More. The contractor tab bar is Home, Work orders, Schedule, Photos, and Account.

## APIs

The app reuses `room-ready/lib/hmore/client.ts` and Auth0. Staff calls live under `room-ready/lib/hmore/services/staff/`.

| Screen | API |
| --- | --- |
| My tenants | `GET /caseload`, `GET /caseload/tenants/{id}` |
| Shifts | `GET /shifts?staff_user_id=` (the caller's own id) |
| Notes | `GET/POST /daily-logs`, `POST /daily-logs/rewrite` |
| Visits | `GET /visits`, `PATCH /visits/{id}` |
| Tasks | `GET /tasks?assigned_user_id=`, `PATCH /tasks/{id}` |
| Incidents | `GET/POST /incidents`. A photo is uploaded with `POST /documents` only when a document category exists, linked as `other`. There is no incident-specific file endpoint. |
| Occupancy | `GET /occupancy-surveys` read only |
| Approvals | `GET /org-workflows/approvals/inbox`, and `POST .../decide` only with `approvals.decide` |
| Alerts | `GET /communications/messages/inbox` and announcements. Inbox items include `related_resource_type` and `related_resource_id` when the message already stored them. |
| Work orders | `GET /maintenance` (the API limits a contractor to assigned work), `POST /maintenance/{id}/transition`, `POST /maintenance/{id}/complete` |
| Scheduling | `GET/POST /maintenance/{id}/visits` and the visit complete route |
| Photos | `POST /maintenance/{id}/files/upload` with `photo_kind=completion` |

Caseload helpers throw before a request unless the mobile role is `support_worker` or `organisation_admin`. The work-order module does not import them.

Status labels are the values returned by the server. The app does not invent an approval.

## Offline drafts

`room-ready/lib/hmore/staff/offlineDrafts.ts` stores a 32-byte key in SecureStore and the draft list in AsyncStorage. SecureStore values are limited to about 2048 bytes, and a daily note can be much larger, so the note body is not written to SecureStore. The AsyncStorage value is XOR-encrypted with the SecureStore key. That hides drafts from a casual read of AsyncStorage. It is not a substitute for device encryption.

Draft types are `daily_log`, `visit_update`, `task_update`, and `work_order_update`. Each draft has a `clientRequestId`. The API does not accept that field, so it is not posted. After a 2xx response the draft is deleted by its id and a later sync does not send it again. A 4xx, 5xx, or network failure leaves the draft on the device. The UI does not say the record is on the server until that 2xx response.

Online detection uses `@react-native-community/netinfo` when the module loads. If it does not, the app pings `GET /health`.

## Voice (F4.4)

Daily notes use device speech first, through `useDeviceSpeechToText` and `expo-speech-recognition`. The hook asks for microphone permission. Partial text is shown while listening and is not written into the note until a final result. Stop commits a leftover partial. Cancel discards it and does not emit text. If the note field is empty, including after Clear, the final text fills it. If the field already has text, including text the staff member edited, the final text is appended after a newline and does not replace the edit. If the native module is missing, permission is denied, or recognition fails, the note field stays usable and the screen says so. An empty capture says that no speech was captured. Package `58.0.1` installs beside Expo 57, but a development build is required before the native module is actually present.

AI professional rewrite is optional. The button calls `POST /api/v1/daily-logs/rewrite` and shows the original beside the rewritten text. Accept copies the rewrite into the note field. Reject leaves the note field as it is. Edit changes the rewritten draft before accept. Report incorrect sends existing AI activity feedback when the response includes an `activity_id`. None of those actions create a daily log. Save original note asks for confirmation, then calls `POST /daily-logs`. Save draft still writes only to the on-device draft store. A disabled feature (403), a usage cap (402), a missing model, or a network error leaves the original note in place and does not claim the rewrite or the save succeeded. The mobile app does not hold an LLM key. Organisation flag `ai.workflow.daily_log_rewrite` is pilot-eligible and stays off until an administrator enables it. See `docs/architecture/VOICE_NOTES_ARCHITECTURE.md`.

## Occupancy

The occupancy screen lists site-survey summaries: status, date, feasibility status, and feasibility summary. It drops any count-shaped fields. Live camera counts are Phase 6 and are not shown, including when the list is empty.

## Push

F4.3 registers an Expo push token after the HMore session is ready and deactivates it on sign-out. Alerts are still the communications inbox. `StaffAlertList` opens a staff record when the message has a known `related_resource_type` and id, or an explicit `hmore://` link in the body. A push tap uses that same `staffAlertHref` helper, then marks the inbox message read when `message_id` is present. The push body is a generic line, not the incident or note text.

Device delivery needs `PUSH_ADAPTER_MODE=expo`, an `EXPO_ACCESS_TOKEN` on the API, and `EXPO_PUBLIC_EAS_PROJECT_ID` on a development or EAS build. Expo Go and the placeholder project id do not deliver a push. See `docs/architecture/PUSH_NOTIFICATIONS_ARCHITECTURE.md`.

## Uploads

Client checks use the API defaults: 10 MB, and JPEG, PNG, or WebP for photos. Documents also allow PDF, plain text, and Word. The server still sniffs the bytes and can reject a file the client accepted.
