# Identity architecture (F1.3)

**Approved provider:** Auth0 (Okta Customer Identity Cloud).  
**Approval:** recorded in the F1.3 implementation thread (Auth0 selected as the single IdP for Next.js, Expo and FastAPI).

## Goals

- Managed identity with provider-backed MFA for staff and admin authentication paths.
- One OIDC identity for web and mobile.
- FastAPI validates access tokens only (JWKS signature, issuer, audience, expiry).
- Map Auth0 `sub` to `users.external_subject` from F1.2.
- Do not trust client-supplied user ids, roles or organisation ids.
- Role enforcement remains F1.4.

## Components

| Layer | Responsibility |
| --- | --- |
| Auth0 tenant | User directory, login, MFA challenges, token issuance |
| `apps/web` | Auth0 Next.js SDK session, login/logout, protected account shell |
| `room-ready` | Auth0 Authorization Code + PKCE, tokens in Expo SecureStore |
| `apps/api` | JWKS verification, `/api/v1/auth/me`, identity upsert by `sub` |

## Token flow

```text
Browser / Expo
    -> Auth0 Universal Login (+ MFA when required)
    -> Authorization code
    -> Tokens (ID token for client identity; access token for API)

API request
    -> Authorization: Bearer <access_token>
    -> FastAPI loads JWKS from https://{AUTH0_DOMAIN}/.well-known/jwks.json
    -> Verify RS256 signature, iss, aud, exp
    -> Read sub (and email when present)
    -> Upsert users.external_subject = sub
```

Access tokens are the only credential the API accepts. Unsigned tokens, wrong issuer, wrong audience, bad signature and expired tokens are rejected with HTTP 401.

## Auth0 tenant and applications

Create the tenant in the **United Kingdom** region when UK residency is required (`*.uk.auth0.com`). Use **Europe** (`*.eu.auth0.com`) only when UK residency is not required and EU residency is acceptable. Do not use a US tenant for HMore production identity data.

Required Auth0 assets:

1. **Regular Web Application** — Next.js dashboard (`apps/web`).
2. **Native Application** — Expo / React Native (`room-ready`).
3. **API (Resource Server)** — identifier equals `AUTH0_AUDIENCE` (example: `https://api.hmore.local`).

Callback and logout URLs are listed in `docs/development/IDENTITY_PROVIDER_SETUP.md`.

## MFA

MFA is enforced in Auth0 (Guardian OTP / provider factors), not by a custom HMore MFA screen. Staff and admin web sign-in must require MFA in the Auth0 tenant. See `docs/development/MFA_CONFIGURATION.md`.

The API can additionally require an MFA authentication-methods claim (`amr` contains `mfa`) when `AUTH0_REQUIRE_MFA_CLAIM=true`. That check is a defence in depth for staff-oriented endpoints; it does not replace Auth0 MFA configuration.

## Identity mapping

| Claim | HMore column |
| --- | --- |
| `sub` | `users.external_subject` (permanent key, unique) |
| `email` | `users.email` (unique; used at first provision only when verified) |
| `name` / `nickname` | `users.display_name` |

Email alone is never the permanent identity key. Account linking to an existing row is allowed only when `external_subject` is still null. Conflicting subjects on the same email are rejected.

Passwords are not stored in HMore.

## Session and logout

- Web: encrypted Auth0 SDK session cookie; logout via Auth0 logout endpoint and local session clear.
- Mobile: access/refresh tokens in SecureStore; logout clears secure storage and ends the Auth0 session when configured.
- API: stateless bearer validation. Revocation of refresh tokens is handled by Auth0; access tokens remain valid until expiry unless Auth0 invalidates them through short lifetimes.

## Out of scope (F1.3)

- Six-role permission matrix (F1.4)
- Organisation isolation enforcement (F1.5)
- Role dashboards (F1.9)
- Replacing Room Ready’s legacy local JWT flows in every screen

## Verification status

Real Auth0 tenant login and MFA must be marked **unverified** until a UK/EU test tenant is configured and exercised. Automated tests in this repository use mocked JWKS and locally signed RS256 tokens only.
