# PROMPT 12 — Old Authentication Architecture Audit

| Field | Value |
| --- | --- |
| Date | 2026-11-16 |
| Git revision | `a2fb515` on `develop` (working tree dirty; ahead of origin by 8) |
| Scope | Local development only — no deploy |
| Decision | Stakeholder: **Auth0 will NOT be used** for HMore application authentication |

---

## 1. Executive summary

HMore today authenticates with **Bearer JWTs**:

1. **Primary (production design):** Auth0 RS256 access tokens validated via JWKS.
2. **Local meeting shortcut:** Demo HS256 tokens (`HMORE_DEMO_AUTH`) issued by `POST /auth/demo/login`.
3. **No first-party password store** on `users` — no native register/login/refresh tables.
4. **RBAC is already provider-agnostic** — roles live on `organisation_memberships`; JWT role claims are not trusted for authorisation.

**Reusable:** User + membership schema, RBAC, RLS headers, `/auth/me`, `/rbac/me`, device sessions, audit hooks, dashboard guard patterns.  
**Must replace:** Auth0 JWKS validation as the active issuer, web `@auth0/nextjs-auth0`, mobile `expo-auth-session` PKCE, Auth0 MFA `amr` assumption, Auth0-first bootstrap docs.

Status of this audit document: **PASS** (complete inventory before deletion).

---

## 2. Existing authentication architecture

```text
[Web Next.js]  --@auth0/nextjs-auth0-->  Auth0 Tenant  --JWT-->  FastAPI JWKS validate
[Mobile Expo]  --PKCE expo-auth-session--> Auth0 Tenant --JWT-->  FastAPI JWKS validate
[Demo web/mobile] --POST /auth/demo/login--> HS256 demo JWT --> FastAPI demo decode
                     |
                     +--> resolve_user_from_claims(sub, email) --> users.external_subject
                     +--> get_authorization_context --> organisation_memberships + permissions
```

| Layer | Mechanism |
| --- | --- |
| API | Stateless Bearer JWT; no global auth middleware — FastAPI `Depends` |
| Identity | `users.external_subject` = IdP `sub`; first-login provision by email |
| Authorisation | DB memberships + `X-Organisation-Id` / `X-HMore-Role` |
| MFA | Claim-only (`amr` contains `mfa`) when `AUTH0_REQUIRE_MFA_CLAIM` |
| Refresh | Auth0-managed; API does not store refresh tokens |
| Web session | Auth0 encrypted cookie; optional demo httpOnly cookie |
| Mobile session | SecureStore / AsyncStorage Auth0 tokens |

---

## 3. Auth0-dependent files (active code)

### API (`apps/api`)

| Path | Role |
| --- | --- |
| `app/auth/tokens.py` | Auth0 JWKS RS256 validation (+ demo first) |
| `app/auth/jwks.py` | Fetch/cache Auth0 JWKS |
| `app/auth/deps.py` | `get_token_claims`, `get_current_user`, MFA deps |
| `app/auth/identity.py` | Map claims → User |
| `app/auth/session_policy.py` | Documents Auth0 as session provider |
| `app/auth/demo.py` | Local demo tokens (not Auth0, but parallel issuer) |
| `app/api/v1/auth.py` | `/auth/me`, `/auth/staff-session`, demo login |
| `app/core/config.py` | `AUTH0_*`, `HMORE_DEMO_*` |
| `app/device_sessions/auth0_management.py` | Optional Auth0 Management API (unused MVP) |
| `app/ops/identity_bootstrap.py` | Pre-grant roles for Auth0 emails |
| `scripts/bootstrap_identity.py` | CLI bootstrap |
| `app/db/models/user.py` | `external_subject` documented as IdP subject |
| Many `tests/test_*.py` | Auth0-shaped / demo tokens |

### Web (`apps/web`)

| Path | Role |
| --- | --- |
| `package.json` | `@auth0/nextjs-auth0` |
| `src/middleware.ts` | Auth0 middleware |
| `src/lib/auth0.ts` | `Auth0Client` |
| `src/lib/authRoutes.ts` | `/auth/login`, `/auth/logout` |
| `src/lib/session.ts` | Session + Bearer for RBAC |
| `src/lib/demoAuth.ts` | Demo cookie helper |
| `src/app/demo-login/page.tsx` | Meeting dummy roles |
| `src/app/(public)/account/page.tsx` | Auth0 session UI |
| `src/components/dashboard/UserMenu.tsx` | Logout via Auth0 |
| `src/app/dashboard/**` (~99 pages) | `auth0.getAccessToken()` BFF pattern |
| `e2e/dashboard.spec.ts` | Auth0 redirect expectations |

### Mobile (`room-ready`)

| Path | Role |
| --- | --- |
| `lib/hmoreAuth0.ts` | PKCE login, refresh, logout |
| `lib/hmoreDemoAuth.ts` | Demo role login (stores via Auth0 token keys) |
| `contexts/AuthContext.tsx` | demo / auth0 / legacy modes |
| `app/(auth)/login.tsx`, `register.tsx` | Auth0 vs demo vs legacy UI |
| `lib/hmore/client.ts` | Bearer from stored Auth0 access token |
| `lib/hmore/security/deviceSessionRevoke.ts` | Revokes Auth0 refresh |
| `components/security/BiometricLockGate.tsx` | Re-auth via Auth0 |

### Tooling / env

| Path | Role |
| --- | --- |
| `apps/api/.env.example` | `AUTH0_*` |
| `apps/web/.env.example` | `AUTH0_*` |
| `room-ready/.env.example` | `EXPO_PUBLIC_AUTH0_*` |
| `scripts/sync-mobile-env-from-web.py` | Sync Auth0 env to mobile |
| `scripts/start-web-dev.ps1`, `start-api-dev.ps1` | Clear/set Auth0 env |

Historical docs/training/ops references: **~200+ markdown files** — classify as migration notes, not active runtime.

---

## 4. Existing database tables (auth-related)

| Table / model | Reuse? |
| --- | --- |
| `users` | **YES** — extend with password + account status |
| `organisation_memberships` | **YES** — approved roles |
| `organisations` | **YES** |
| `mobile_device_sessions` | **YES** — keep as device registry |
| `audit_events` | **YES** — auth audit can write here and/or dedicated table |
| Password / refresh / registration request tables | **MISSING** — must add |
| In-app auth notification table | **MISSING** — add dedicated table (M11 message inbox is org messaging, not ideal for registration alerts) |

**Six roles (unchanged):**  
`super_admin`, `organisation_admin`, `landlord`, `tenant`, `support_worker`, `maintenance_contractor`

Membership statuses today: `active`, `invited`, `suspended` — account lifecycle for registration needs **user-level** status (pending / approved / rejected / suspended / disabled).

---

## 5. Existing authentication APIs

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/auth/staff-session` | MFA flag from claims |
| POST | `/api/v1/auth/demo/login` | Dev-only role tokens |
| GET | `/api/v1/auth/demo/roles` | Demo catalogue |
| GET | `/api/v1/rbac/me` | Active role + permissions |
| POST | `/api/v1/rbac/memberships` | Assign memberships |
| Device session routes | `/api/v1/device-sessions/*` | Installation lifecycle |

**Missing for native auth:** register, login, logout, refresh, password reset/change, registration approval, auth notifications, Super Admin create Org Admin.

---

## 6. Security middleware / deps (reusable)

- `get_current_user` / `get_token_claims`
- `get_authorization_context` / `require_perm`
- Tenancy RLS (`get_organisation_context`)
- CORS + security headers
- Device session header guard

These stay; only the **token issuer/validator** behind `get_token_claims` changes.

---

## 7. Frontend contexts & protected routes

| Surface | Pattern |
| --- | --- |
| Web | Middleware → Auth0 routes; dashboard pages call `requireAuthenticatedSession` + `getAccessToken` |
| Mobile | `AuthContext` gates `(app)` layout; SecureStore tokens |

Demo paths already prove Bearer → `/rbac/me` works without Auth0 for meetings.

---

## 8. Environment variables (Auth0 / demo)

| Variable | Surface |
| --- | --- |
| `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_ISSUER` | API |
| `AUTH0_REQUIRE_MFA_CLAIM`, `AUTH0_MGMT_*` | API |
| `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`, `AUTH0_SECRET`, `APP_BASE_URL` | Web |
| `EXPO_PUBLIC_AUTH0_*` | Mobile |
| `HMORE_DEMO_AUTH`, `HMORE_DEMO_AUTH_SECRET`, `HMORE_DEMO_ORG_*` | API demo |
| `NEXT_PUBLIC_DEMO_AUTH`, `EXPO_PUBLIC_DEMO_AUTH` | Clients |

**To add for native:** signing secrets, access/refresh TTLs, lockout settings, cookie names, CSRF secret.

---

## 9. Features to reuse vs replace

### Reuse

- `User` + `OrganisationMembership` + six-role RBAC matrix
- `/auth/me`, `/rbac/me`, permission deps, RLS
- Web dashboard role homes and permission checks
- Mobile `hmore/client` Bearer transport + secure storage abstraction
- Demo login as temporary meeting tool until native login UI ships (then keep only behind explicit demo flag)
- Audit event framework

### Replace / add

- Active Auth0 JWKS path as default issuer
- Web Auth0 SDK middleware and login/logout URLs
- Mobile Auth0 PKCE module as default mode
- Password hashing, registration approval workflow, refresh token store
- Native MFA (optional later) — document as **not** claim-from-Auth0
- Bootstrap scripts / docs that assume Auth0 email first login

---

## 10. Migration risks

| Risk | Mitigation |
| --- | --- |
| Existing `external_subject` Auth0 `sub` values | Keep column; native users use `hmore\|{user_id}` subjects; link by email when migrating |
| ~99 web pages call `auth0.getAccessToken()` | Introduce native token helper / compatibility shim so pages keep working |
| Production config requires Auth0 today | Gate native as default locally; Auth0 path only if explicitly re-enabled (should stay off per stakeholder) |
| Stateless JWT revocation | Store refresh tokens + revoke list / session rows; short access TTL |
| Demo auth backdoor | Keep demo gated to development environments only |
| Do not reset DB / delete users | Additive Alembic migration only |
| MFA regression | Staff MFA via Auth0 `amr` will not apply; document native MFA as follow-up unless scoped in |
| Dual login confusion | Remove Auth0 from active UI paths; no hidden Auth0 fallback |

---

## 11. Git status at audit start

- Branch: `develop` (ahead of `origin/develop` by 8 commits)
- Dirty tree: demo auth, mobile fetch fixes, audit docs, env changes (from prior meeting work)
- **No commit/push performed by this prompt** (per rules)

---

## 12. Audit conclusion

| Item | Status |
| --- | --- |
| Auth0 dependency inventory | **PASS** |
| Reusable RBAC/identity identified | **PASS** |
| Gaps for native register/login/approval identified | **PASS** |
| Auth0 code deleted before inventory | **N/A** (not deleted) |
| Ready to implement native auth | **PASS** — proceed Parts 2–15 |

*Auth0 packages and modules remain until native auth is proven; removal tracked in `PROMPT_12_AUTH0_REMOVAL_REPORT.md`.*
