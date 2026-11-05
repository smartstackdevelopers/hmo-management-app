# Session Control (F1.4)

## Architecture

HMore does not operate a second session store for API access tokens. Auth0 issues tokens; FastAPI validates them on each request (F1.3). F1.4 adds authorization freshness and documents logout/revocation behaviour.

## Validation

- Missing Bearer token → 401
- Invalid signature / wrong audience / wrong issuer → 401
- Expired `exp` → 401
- Valid token with no active membership → 403 on RBAC routes requiring context

## Logout

| Client | Behaviour |
| --- | --- |
| Web (`apps/web`) | `/auth/logout` via Auth0 Next.js SDK clears the app session cookie and Auth0 SSO session |
| Mobile (future / Expo) | Clear SecureStore tokens and call Auth0 logout |

Logout does not invent a HMore-side token blacklist.

## Revocation strategy (Auth0 limitations)

- Refresh tokens: revoke via Auth0 (Dashboard, Management API, or logout with federated logout where configured).
- Access tokens: remain valid until `exp`. Mitigate with short access-token lifetimes in the Auth0 API settings.
- HMore does **not** claim mid-lifetime access-token kill switches beyond Auth0 capabilities.

## Role changes during an active session

1. Administrator updates membership via `POST /api/v1/rbac/memberships`.
2. Target `users.authorization_version` increments.
3. Clients should re-fetch `GET /api/v1/rbac/me` and compare `authorization_version`.
4. Cached frontend permission lists must be discarded when the version changes.
5. Next API call loads memberships from the database — authorization is never taken from a stale client permission list.

## API surface

- `GET /api/v1/rbac/session` — session policy summary + current `authorization_version`
- `GET /api/v1/rbac/me` — includes `session` payload
- `GET /api/v1/auth/me` — includes `authorization_version` for clients that already poll identity

## Sensitive data

Do not log access tokens, refresh tokens, or Authorization headers. Session policy responses describe behaviour only.

## Reauthentication

Staff MFA continues to follow F1.3 (`AUTH0_REQUIRE_MFA_CLAIM` / `amr`). Session control does not replace MFA.
