# Auth0 identity provider setup

Never commit real Client Secrets, AUTH0_SECRET values, or Management API tokens.

## 1. Create a UK or EU tenant

1. Sign in to the Auth0 Dashboard.
2. Create a tenant.
3. Choose region **United Kingdom** for UK data residency (`your-tenant.uk.auth0.com`), or **Europe** for EU residency (`your-tenant.eu.auth0.com`).
4. Do not create the HMore production tenant in the United States.

Record the domain (without `https://`) as `AUTH0_DOMAIN`.

## 2. Create the API (resource server)

1. Applications → APIs → Create API.
2. Name: `HMore API`.
3. Identifier: a stable URI, for example `https://api.hmore.local`.
4. Signing algorithm: RS256.

This identifier is `AUTH0_AUDIENCE` for FastAPI and for clients requesting access tokens.

Enable RBAC later in F1.4 if Auth0 permissions are used. F1.3 does not enforce HMore roles from Auth0.

## 3. Create the Regular Web Application

1. Applications → Create Application → Regular Web Application.
2. Allowed Callback URLs: `http://localhost:3000/auth/callback`
3. Allowed Logout URLs: `http://localhost:3000`
4. Allowed Web Origins: `http://localhost:3000`
5. Copy Domain, Client ID, Client Secret into the web env file.

Add production URLs when deploying.

## 4. Create the Native Application (Expo)

1. Applications → Create Application → Native.
2. Allowed Callback URLs (Expo):  
   `roomready://auth/callback`  
   plus the Expo AuthSession redirect URI printed by `AuthSession.makeRedirectUri` for your build.
3. Allowed Logout URLs: `roomready://`
4. Application Type: Native. Enable OIDC Conformant.
5. Copy Client ID into mobile config. Native apps are public clients (no client secret in the app).
6. Add an Auth0 Action (or API authorization) so access tokens include `email` and `email_verified` for first-time FastAPI provisioning.

## 5. Environment variables

### FastAPI (`apps/api/.env`)

```text
AUTH0_DOMAIN=your-tenant.uk.auth0.com
AUTH0_AUDIENCE=https://api.hmore.local
AUTH0_ISSUER=https://your-tenant.uk.auth0.com/
AUTH0_REQUIRE_MFA_CLAIM=false
```

`AUTH0_ISSUER` must include the trailing slash and match the access-token `iss` claim. If omitted, the API derives `https://{AUTH0_DOMAIN}/`.

### Next.js (`apps/web/.env.local`)

```text
AUTH0_DOMAIN=your-tenant.uk.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
AUTH0_SECRET=  # openssl rand -hex 32
APP_BASE_URL=http://localhost:3000
AUTH0_AUDIENCE=https://api.hmore.local
```

### Expo (`room-ready` app config / env)

```text
EXPO_PUBLIC_AUTH0_DOMAIN=your-tenant.uk.auth0.com
EXPO_PUBLIC_AUTH0_CLIENT_ID=...
EXPO_PUBLIC_AUTH0_AUDIENCE=https://api.hmore.local
EXPO_PUBLIC_AUTH0_SCHEME=roomready
```

Mobile helpers live in `room-ready/lib/hmoreAuth0.ts` and use Expo SecureStore. They do not replace the legacy local JWT AuthContext until a cut-over task is scheduled.

## 6. Grant the web app access to the API

In the Regular Web Application settings, authorize the HMore API and request the audience from the Auth0 Next.js client (`authorizationParameters.audience`).

## 7. Local smoke checklist (real tenant)

1. Open `http://localhost:3000/auth/login`.
2. Complete Auth0 Universal Login and MFA (staff path).
3. Land on `/account` with a session.
4. Call `GET /api/v1/auth/me` with a Bearer access token; confirm `external_subject` is stored.
5. Confirm logout clears the web session.

Until this checklist is run against a real UK/EU tenant, mark web/mobile MFA integration **unverified**.

## Privacy notes

- Prefer UK region for UK operational data residency.
- Limit Auth0 user profile fields to identity needs (email, name). Do not store special-category data in Auth0 metadata.
- Review Auth0 DPA / data processing terms with the client before production go-live.
