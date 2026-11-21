# PROMPT 2 — Auth0 authentication audit

**Date:** 2026-11-14 (follow-up completed same day)  
**Branch:** `develop` @ `95bed7a` (`docs(audit): Prompt 2 auth, RBAC and security verification`)  
**Scope:** Local code/config review + automated tests. No `.env` secrets read. Examples only: `apps/api/.env.example`, `apps/web/.env.example`, `room-ready/.env.example`.

## Overall verdict

| Area | Verdict | Rationale |
| --- | --- | --- |
| Auth0 integration (API token validation) | **PASS** | JWKS RS256, `aud`/`iss`/`sub` enforced; `tests/test_auth_tokens.py` (mock JWKS) |
| Auth0 web session (`@auth0/nextjs-auth0`) | **PARTIAL** | Middleware + audience in code; live tenant login not run without secrets |
| Auth0 mobile (Expo PKCE) | **PARTIAL** | `room-ready/lib/hmoreAuth0.ts`; legacy mode when Auth0 env unset |
| User mapping / provisioning | **PASS** | `app/auth/identity.py`; `tests/test_auth_identity.py` |
| Logout (code paths) | **PASS** | Web `/auth/logout` (SDK); mobile `logoutAuth0` + token clear — see § Logout |
| Logout (live session) | **UNVERIFIED** | No browser/Expo run with real Auth0 |
| MFA | **UNVERIFIED** | Docs only; no tenant evidence in repo |
| Six real Auth0 users (E2E) | **UNVERIFIED** | Placeholders in `scripts/meeting-six-roles.env.example` |

---

## API surface (`API_V1_PREFIX=/api/v1`)

| Endpoint | File | Auth dependency | Purpose |
| --- | --- | --- | --- |
| `GET /api/v1/auth/me` | `app/api/v1/auth.py` | `get_current_user` + `get_token_claims` | HMore user from Auth0 `sub` |
| `GET /api/v1/auth/staff-session` | `app/api/v1/auth.py` | `get_staff_user`, `require_mfa` | Staff probe; MFA when `AUTH0_REQUIRE_MFA_CLAIM=true` |
| `GET /api/v1/rbac/me` | `app/api/v1/rbac.py` | `get_authorization_context` | Active role, org, permissions (web uses this) |
| `GET /api/v1/rbac/roles` | `app/api/v1/rbac.py` | `get_authorization_context` | Six role definitions |
| `GET /api/v1/rbac/permissions` | `app/api/v1/rbac.py` | `get_authorization_context` | Permission catalog |
| `GET /api/v1/rbac/matrix` | `app/api/v1/rbac.py` | `require_perm(AUDIT_LOGS_READ)` | Full role→permission matrix |
| `GET /api/v1/rbac/session` | `app/api/v1/rbac.py` | `get_authorization_context` | Session policy payload |
| `POST /api/v1/rbac/memberships` | `app/api/v1/rbac.py` | `get_authorization_context` | Role assignment (gated in service) |
| `GET /api/v1/isolation/properties` | `app/api/v1/isolation_probes.py` | `require_perm(PROPERTIES_READ)` + org context | Org-scoped property list |
| `POST /api/v1/isolation/properties` | `app/api/v1/isolation_probes.py` | `require_perm(PROPERTIES_MANAGE)` + org context | Create property in trusted org |
| `POST /api/v1/organisations` | `app/api/v1/organisations.py` | `get_platform_context` | Super Admin org create |
| `GET /api/v1/platform-governance/platform/organisations` | `app/api/v1/platform_governance.py` | platform + governance addon | Super Admin org list |

Router registration: `app/api/v1/router.py`.

---

## Task 1 — Auth0 implementation paths

### API (`apps/api`)

| Concern | Path |
| --- | --- |
| Token validation (JWT access) | `app/auth/tokens.py` — RS256 via `app/auth/jwks.py`; claims `exp`, `iss`, `aud`, `sub` |
| Bearer dependency | `app/auth/deps.py` — `get_token_claims`, `get_current_user` |
| Identity mapping | `app/auth/identity.py` — `resolve_user_from_claims` (email link on first login) |
| MFA gate (optional) | `app/auth/deps.py` — `require_mfa`, `token_has_mfa` (`amr` contains `mfa`) |
| Config | `app/core/config.py` — `auth0_domain`, `auth0_audience`, `auth0_issuer`, `auth0_require_mfa_claim` |
| RBAC after auth | `app/rbac/deps.py` — DB memberships; headers `X-Organisation-Id`, `X-HMore-Role`, `X-Device-Session-Id` |
| Example env | `apps/api/.env.example` |

### Web (`apps/web`)

| Concern | Path |
| --- | --- |
| Auth0 client | `src/lib/auth0.ts` — `Auth0Client`, `scope: openid profile email offline_access`, optional `AUTH0_AUDIENCE` |
| Middleware | `src/middleware.ts` — `auth0.middleware(request)` when configured |
| Session + RBAC | `src/lib/session.ts` — `fetch(`${API_BASE}/api/v1/rbac/me`)` with access token |
| Login path constant | `src/lib/rbac.ts` — `LOGIN_PATH = "/auth/login"` |
| Logout constant | `src/lib/authRoutes.ts` — `LOGOUT_HREF = "/auth/logout"` |
| Account / redirects | `src/app/(public)/account/page.tsx` — redirect to `/auth/login?returnTo=/account` when no session |
| Example env | `apps/web/.env.example` — `AUTH0_*`, `APP_BASE_URL`, `NEXT_PUBLIC_API_BASE_URL` |

Auth0 App Router routes (`/auth/login`, `/auth/logout`, `/auth/callback`, …) are provided by `@auth0/nextjs-auth0` via middleware — no local `route.ts` under `src/app/auth/`.

### Mobile (`room-ready`)

| Concern | Path |
| --- | --- |
| PKCE login | `lib/hmoreAuth0.ts` — `loginWithAuth0`, discovery `authorizationEndpoint` / `tokenEndpoint` |
| Token storage | SecureStore keys `hmore.auth0.accessToken`, `refreshToken`, `idToken`, `expiresAt` |
| Refresh | `accessTokenNeedsRefresh`, refresh-token grant in `hmoreAuth0.ts` |
| Logout | `logoutAuth0` — `clearAuth0Tokens()` then `https://{domain}/v2/logout?...` via `WebBrowser.openAuthSessionAsync` |
| App wiring | `contexts/AuthContext.tsx` — `signOut()` → `logoutAuth0()` when `authMode === 'auth0'` |
| Legacy fallback | `authMode: 'legacy'` when `EXPO_PUBLIC_AUTH0_DOMAIN` / `CLIENT_ID` missing |
| Example env | `room-ready/.env.example` — `EXPO_PUBLIC_AUTH0_*`, `EXPO_PUBLIC_HMORE_API_URL` |

---

## Logout — code verification (no secrets)

| Client | Entry UI | Code path | Target |
| --- | --- | --- | --- |
| Web | `src/components/dashboard/UserMenu.tsx`, `DashboardShell.tsx`, `(public)/account/page.tsx` | `<a href="/auth/logout">` or `LOGOUT_HREF` | Auth0 SDK logout route |
| Web | `src/middleware.ts` | SDK handles session cookie clear on `/auth/logout` | Auth0 tenant |
| Mobile | `components/tenant/HmoreAccount.tsx`, `app/(app)/(tabs)/more.tsx`, `settings.tsx`, `StaffMore.tsx` | `useAuth().signOut()` | `contexts/AuthContext.tsx` |
| Mobile | `DeviceSecurityPanel.tsx`, `BiometricLockGate.tsx` | security flows call `signOut()` | same |
| Mobile | `lib/hmoreAuth0.ts` `logoutAuth0` | delete SecureStore tokens; optional `v2/logout` browser session | `buildAuth0Discovery().endSessionEndpoint` |

**Code verdict:** **PASS** — consistent logout hooks; no alternate “silent” bypass in repo.  
**Live verdict:** **UNVERIFIED** — confirm Auth0 “Allowed Logout URLs” includes `APP_BASE_URL` and mobile `returnTo` redirect URI.

---

## Task 5 — MFA

| Item | Status |
| --- | --- |
| Auth0 tenant MFA policy | **UNVERIFIED** — not in repo |
| Documentation | `docs/development/MFA_CONFIGURATION.md` |
| API enforcement | `GET /api/v1/auth/staff-session` + `AUTH0_REQUIRE_MFA_CLAIM` |
| Default | `AUTH0_REQUIRE_MFA_CLAIM=false` in `apps/api/.env.example` |
| Unit tests | `tests/test_auth_tokens.py` — `token_has_mfa`, mocked claims only |

**Verdict: UNVERIFIED** for production/staff login until Auth0 dashboard policy is applied and tested.

---

## Task 6 — Six Auth0 users

| Source | Path |
| --- | --- |
| Onboarding guide | `docs/development/FULL_AUTH_ONBOARDING.md` |
| Acceptance checklist | `docs/development/ROLE_ACCEPTANCE_CHECKLIST.csv` |
| Email template (no secrets) | `scripts/meeting-six-roles.env.example` |
| Bootstrap all roles | `scripts/bootstrap-all-six-roles.ps1` → `scripts/bootstrap-identity.ps1` |
| CLI | `apps/api/scripts/bootstrap_identity.py` |

Detailed manual steps: `docs/audit/PROMPT_2_REMAINING_ISSUES.md` § Six-role local verification.

---

## Test evidence (auth-focused, follow-up run)

| Suite | Result |
| --- | --- |
| Focused security/RBAC command (see `PROMPT_2_SECURITY_TEST_REPORT.md`) | **34 passed**, **18 skipped**, 0 failed |
| Full `apps/api` pytest | **415 passed**, **116 skipped**, 0 failed |
| Web typecheck | **PASS** (`npm run typecheck`, no source changes) |
| `room-ready` Jest `tenantMobile` (prior Prompt 2) | **14 passed** |

JWT / token tests: `apps/api/tests/test_auth_tokens.py` (9 passed in isolated run; mock JWKS, not live Auth0).

---

## References

- `docs/audit/PROMPT_1_TEST_REPORT.md`, `PROMPT_1_FIX_REPORT.md`
- `docs/audit/FEATURE_56_STATUS.csv` (M01.1–M01.3)
- `docs/audit/SIX_ROLE_ACCESS_VERIFICATION.md`