# Tenant mobile architecture (F4.1)

The tenant mobile app is the Expo project in `room-ready/`. `apps/mobile` stays a pointer. This release wires that app to the FastAPI `/api/v1` API for a signed-in tenant. Staff mobile (F4.2) and push are separate. F4.5 adds offline repair drafts: if the repair form is offline, the repair and its photos stay on the device until Sync Now or a reconnect sync gets a 2xx. See `docs/architecture/OFFLINE_SYNC_ARCHITECTURE.md`.

## Sign-in

When `EXPO_PUBLIC_AUTH0_DOMAIN` and `EXPO_PUBLIC_AUTH0_CLIENT_ID` are set, sign-in is Auth0 Authorization Code + PKCE (`room-ready/lib/hmoreAuth0.ts`). Tokens are stored in SecureStore. Before the access token expires, the app uses the refresh-token grant. Tokens are not written to logs.

Password sign-in against the legacy Room Ready API remains only when those Auth0 variables are unset.

After Auth0, the app calls `GET /auth/me` and `GET /rbac/me`, then sends `X-Organisation-Id` and `X-HMore-Role` on later requests.

## Tenant surfaces

| Area | API | Behaviour |
| --- | --- | --- |
| Home and profile | `GET /tenant/me`, `PATCH /tenant/me` | Own row only. The tenant can change `preferred_name` and `phone`. The response omits notes, consent notes, and needs/goals. Staff `PATCH /tenants/{id}` stays forbidden for the tenant role. |
| Housing | `GET /tenant/me/housing`, `GET /housing-applications` | Shows the assigned property and room when those foreign keys are set. If nothing is assigned, the screen says housing has not been assigned. Addresses are not invented. |
| Repairs | `GET/POST /maintenance`, photo upload | A new repair uses `assigned_property_id` from `/tenant/me/housing`. If that property is null, the form explains that staff must assign housing before a repair can be sent. Photos can be previewed and removed before submit. Emergency priority is not offered; immediate danger is directed to 999. |
| Support | `GET /tenant/support-plans`, timeline appointments | Read-only plan, appointments, and recent timeline items the tenant can view. |
| Files | `GET /documents`, `POST /tenant/me/documents` | Existing list and content endpoints stay the read path. A tenant can upload a PDF or image for their own record. That upload does not grant general `documents.upload`. |
| Alerts | Communications inbox and announcements | In-app messages can be marked read. |
| Assistant | `/tenant-assistant`, `POST /ai-activity/{activity_id}/feedback` | Asks only when the pilot says the assistant is available. If the ask response includes an activity id, the tenant can send wrong-answer feedback. If it does not, sources already returned are shown and feedback is not reported as sent. Answers are not official decisions. |
| Local services | `GET /community-services?q=&category=` | Published rows for the caller's organisation. An empty list is valid. There is no sample catalogue and no postcode search. |
| Jobs and training | `GET /opportunities?kind=&q=` | Published job rows require `jobs.discover`. Training rows require `training.discover`. Empty catalogues stay empty. |
| Language and accessibility | device storage | Text size, contrast, and a saved language preference. The picker offers English and Urdu. A missing translation falls back to English. |

Tabs for a tenant are Home, My home, Repairs, Support, and Account.

## Client

`room-ready/lib/hmore/client.ts` is the typed fetch wrapper. Failures become `HmoreApiError` with the API `detail` string. The Authorization header is attached in memory and is not logged.
