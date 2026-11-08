# Tenant mobile setup (F4.1)

The Expo app lives in `room-ready/`. From the monorepo root:

```bash
npm install
npm run typecheck -w room-ready
npm test -w room-ready
npm run start -w room-ready
```

## API

Run the FastAPI app on port 8000. The mobile client calls `/api/v1`.

Set the base explicitly when the device cannot reach the dev host:

```bash
EXPO_PUBLIC_HMORE_API_URL=http://localhost:8000/api/v1
```

If that variable is unset, the app uses `http://<dev-host>:8000/api/v1`. Android emulators use `10.0.2.2`. Copy `room-ready/.env.example` to `room-ready/.env` and fill in public values only. Do not put an Auth0 client secret in the app.

## Auth0

Create a Native application in a UK or EU Auth0 tenant and set:

```bash
EXPO_PUBLIC_AUTH0_DOMAIN=your-tenant.uk.auth0.com
EXPO_PUBLIC_AUTH0_CLIENT_ID=
EXPO_PUBLIC_AUTH0_AUDIENCE=https://api.hmore.local
EXPO_PUBLIC_AUTH0_SCHEME=roomready
```

Allowed callback and logout URLs must include the Expo redirect (`roomready://auth/callback`, plus the Expo dev redirect while you are developing). Enable the refresh token / offline access grant so the app can renew the access token.

The API still expects a user mapped from the Auth0 subject, an active tenant membership, and `X-Organisation-Id` / `X-HMore-Role` when the user has more than one membership. The app stores the active organisation and role from `GET /rbac/me`.

Leave the Auth0 variables unset only if you still need the legacy Room Ready password API (`EXPO_PUBLIC_API_URL`, default port 3001).

## What you should see

A tenant can open housing details, repairs, support, documents, notifications, the assistant (when the pilot organisation is enabled), and accessibility settings. Local services and jobs explain that they depend on Phase 5 and do not show sample listings. Profile fields are read-only.

## Known limitations

- New repair reports need a `property_id`. The tenant role cannot list properties, so the form reuses `preferred_property_id` from housing applications or an existing repair. If none exist, the form explains that staff must link a property first.
- There is no `/tenant/me` bootstrap aggregate; the app uses `GET /tenants` (own row) plus related modules.
- Community directory and jobs/training listings are Phase 5 — screens show a dependency notice only.
- In-app notifications use the communications inbox. Device push is F4.3 (not included).
- Emulator/device UI passes are environment-dependent; CI covers typecheck and unit tests.
