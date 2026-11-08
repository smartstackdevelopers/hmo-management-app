# Tenant mobile architecture (F4.1)

The tenant mobile app is the Expo project in `room-ready/`. `apps/mobile` stays a pointer. This release wires that app to the FastAPI `/api/v1` API for a signed-in tenant. Staff mobile (F4.2), push, biometrics, and offline drafts are out of scope.

## Sign-in

When `EXPO_PUBLIC_AUTH0_DOMAIN` and `EXPO_PUBLIC_AUTH0_CLIENT_ID` are set, sign-in is Auth0 Authorization Code + PKCE (`room-ready/lib/hmoreAuth0.ts`). Tokens are stored in SecureStore. Before the access token expires, the app uses the refresh-token grant. Tokens are not written to logs.

Password sign-in against the legacy Room Ready API remains only when those Auth0 variables are unset.

After Auth0, the app calls `GET /auth/me` and `GET /rbac/me`, then sends `X-Organisation-Id` and `X-HMore-Role` on later requests.

## Tenant surfaces

| Area | API | Behaviour |
| --- | --- | --- |
| Home and profile | `GET /tenants` | Own row only. Read-only. The app does not call `PATCH /tenants`. |
| Housing | `GET /tenants`, `GET /housing-applications` | Shows the linked housing record and the tenant's applications. |
| Repairs | `GET/POST /maintenance`, photo upload | Tenants can report a repair when a property id is already on an application or an existing repair. Emergency priority is not offered; immediate danger is directed to 999. |
| Support | `GET /tenant/support-plans`, timeline appointments | Read-only plan, appointments, and recent timeline items the tenant can view. |
| Files | `GET /documents` | Metadata, plus an authenticated content fetch. |
| Alerts | Communications inbox and announcements | In-app messages can be marked read. |
| Assistant | `/tenant-assistant` | Asks only when the pilot says the assistant is available. Answers are not official decisions. |
| Local services, jobs | none | UI returns `phase5_pending`. No sample listings. |
| Language and accessibility | device storage | Text size, contrast, and a saved language preference. |

Tabs for a tenant are Home, My home, Repairs, Support, and Account.

## Client

`room-ready/lib/hmore/client.ts` is the typed fetch wrapper. Failures become `HmoreApiError` with the API `detail` string. The Authorization header is attached in memory and is not logged.
