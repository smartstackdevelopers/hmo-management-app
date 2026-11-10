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

Tenant calls used by this app include `GET` and `PATCH /tenant/me`, `GET /tenant/me/housing`, `POST /tenant/me/documents`, `GET /community-services`, and `GET /opportunities`. Those catalogue endpoints return an empty list until an organisation admin publishes rows. No sample listings are shipped with the app.

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

A tenant can open assigned housing, repairs, support, documents (including their own PDF or image submission), notifications, the assistant (when the pilot organisation is enabled), local services, jobs and training, and accessibility settings. Community services and opportunities show only published rows for the signed-in organisation. If none have been published, the screen says no verified listings have been published for this organisation. Preferred name and phone can be saved from Account; other profile fields stay with staff. English and Urdu are the languages in the picker.

## Known limitations

- A new repair needs an assigned property. `GET /tenant/me/housing` returns that property id when staff have set `assigned_property_id`. If the property is null, the form explains that staff must assign housing before a new repair can be sent.
- Catalogue tables start empty. Nothing in the migration inserts food banks, jobs, training, or housing.
- In-app notifications use the communications inbox. Device push is F4.3 (not included).
- iOS and Android device runs were not executed in CI. CI covers typecheck and unit tests. Auth0 still has to be configured on a real tenant before a signed-in device session works.
