# Mobile (Expo)

The tenant mobile app for F4.1 is the Expo project in [`../../room-ready`](../../room-ready). This folder stays a pointer so import paths, EAS, and CI can move together later. Do not treat Expo web as the HMore admin dashboard; that is `apps/web`.

`room-ready` signs in with Auth0 PKCE when configured and calls the FastAPI `/api/v1` API. Tenant tabs are Home, My home, Repairs, Support, and Account. Housing comes from `GET /api/v1/tenants` (the caller's own row) and is read-only. Local services and jobs stay empty until Phase 5 (`phase5_pending`) — the app does not ship sample listings.

Setup and the request flow: [`../../docs/development/TENANT_MOBILE_SETUP.md`](../../docs/development/TENANT_MOBILE_SETUP.md) and [`../../docs/architecture/TENANT_MOBILE_ARCHITECTURE.md`](../../docs/architecture/TENANT_MOBILE_ARCHITECTURE.md).

```bash
npm run typecheck -w room-ready
npm test -w room-ready
```
