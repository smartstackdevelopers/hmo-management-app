# Mobile (Expo)

The Expo app for tenants (F4.1) and staff (F4.2) is [`../../room-ready`](../../room-ready). This folder stays a pointer so import paths, EAS, and CI can move together later. Do not treat Expo web as the HMore admin dashboard; that is `apps/web`.

`room-ready` signs in with Auth0 PKCE when configured and calls the FastAPI `/api/v1` API. Tenant tabs are Home, My home, Repairs, Support, and Account. Support workers and organisation admins get caseload, shifts, notes, and the rest of the staff screens. Maintenance contractors get assigned work orders. Live occupancy counts are not in this build. Push registration is wired (F4.3) but a device does not receive a notification unless the API has Expo credentials and the app has a real EAS project id. See [`../../docs/development/PUSH_NOTIFICATIONS_SETUP.md`](../../docs/development/PUSH_NOTIFICATIONS_SETUP.md).

Setup: [`../../docs/development/TENANT_MOBILE_SETUP.md`](../../docs/development/TENANT_MOBILE_SETUP.md), [`../../docs/development/STAFF_MOBILE_SETUP.md`](../../docs/development/STAFF_MOBILE_SETUP.md), [`../../docs/architecture/TENANT_MOBILE_ARCHITECTURE.md`](../../docs/architecture/TENANT_MOBILE_ARCHITECTURE.md), and [`../../docs/architecture/STAFF_MOBILE_ARCHITECTURE.md`](../../docs/architecture/STAFF_MOBILE_ARCHITECTURE.md).

```bash
npm run typecheck -w room-ready
npm test -w room-ready
```
