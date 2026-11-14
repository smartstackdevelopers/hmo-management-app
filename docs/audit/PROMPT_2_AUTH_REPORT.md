# PROMPT 2 — Auth0 authentication audit

**Date:** 2026-11-14  
**Branch:** `develop` @ `0ae8d07` (Prompt 1 commit; local, not pushed)  
**Scope:** Local code/config review + automated tests. No `.env` secrets read. Examples only: `apps/api/.env.example`, `apps/web/.env.example`, `room-ready/.env.example`.

## Overall verdict

| Area | Verdict | Rationale |
| --- | --- | --- |
| Auth0 integration (API token validation) | **PASS** | JWKS RS256, `aud`/`iss`/`sub` enforced; mocked tests green |
| Auth0 web session (`@auth0/nextjs-auth0`) | **PARTIAL** | Middleware + audience configured in code; live tenant login not run this session |
| Auth0 mobile (Expo PKCE) | **PARTIAL** | `room-ready/lib/hmoreAuth0.ts` parity with API audience; legacy login remains when Auth0 env unset |
| User mapping / provisioning | **PASS** | `app/auth/identity.py` links `sub` ↔ email; tests in `test_auth_identity.py` |
| Logout | **PARTIAL** | Web: `/auth/logout` via Auth0 SDK middleware; mobile: `logoutAuth0` + token clear — not browser-verified |
| MFA | **UNVERIFIED** | Policy documented only; `AUTH0_REQUIRE_MFA_CLAIM` default false |
| Six real Auth0 users (E2E) | **UNVERIFIED** | Placeholder emails in `scripts/meeting-six-roles.env.example` only |

---

## Task 1 — Auth0 paths

### API (`apps/api`)

| Concern | Path |
| --- | --- |
| Token validation | `app/auth/tokens.py` — JWKS from `app/auth/jwks.py`, audience `AUTH0_AUDIENCE`, issuer `AUTH0_ISSUER` or `https://{AUTH0_DOMAIN}/` |
| Bearer dependency | `app/auth/deps.py` — `get_token_claims`, `get_current_user` |
| Identity mapping | `app/auth/identity.py` — `resolve_user_from_claims` |
| MFA gate (optional) | `app/auth/deps.py` — `require_mfa`, `get_staff_user`; enabled when `auth0_require_mfa_claim=true` (`app/core/config.py`) |
| Staff probe | `app/api/v1/auth.py` — `GET /api/v1/auth/me`, `GET /api/v1/auth/staff-session` |
| RBAC after auth | `app/rbac/deps.py` — memberships from DB; headers `X-Organisation-Id`, `X-HMore-Role` select among assigned memberships only |
| Config surface | `apps/api/.env.example` — `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_ISSUER`, `AUTH0_REQUIRE_MFA_CLAIM` |

### Web (`apps/web`)

| Concern | Path |
| --- | --- |
| Auth0 client | `src/lib/auth0.ts` — `Auth0Client`, optional `AUTH0_AUDIENCE` on authorize |
| Middleware | `src/middleware.ts` — global matcher; no-op when Auth0 env missing (CI-safe) |
| Session + API RBAC | `src/lib/session.ts` — `getDashboardSession()` calls `GET /api/v1/rbac/me` with access token |
| Login / account | `src/app/(public)/account/page.tsx`, Auth0 routes under `/auth/*` (SDK) |
| Logout href | `src/lib/authRoutes.ts` — `LOGOUT_HREF = "/auth/logout"` |
| Config | `apps/web/.env.example` — domain, client, secret, `APP_BASE_URL`, `AUTH0_AUDIENCE` |

### Mobile (`room-ready`)

| Concern | Path |
| --- | --- |
| Auth0 PKCE | `lib/hmoreAuth0.ts` — authorize/token/revoke, SecureStore keys |
| App wiring | `contexts/AuthContext.tsx` — `authMode: 'auth0' \| 'legacy'` |
| API calls | `lib/hmore/client.ts` (via tests), bearer + org headers |
| Legacy guard | `lib/legacyApiConfig.ts` — throws if `EXPO_PUBLIC_API_URL` unset (no port 3001 default) |
| Config | `room-ready/.env.example` — `EXPO_PUBLIC_AUTH0_*`, `EXPO_PUBLIC_HMORE_API_URL` |

### Mobile vs web parity

- Same API audience pattern (`EXPO_PUBLIC_AUTH0_AUDIENCE` / web `AUTH0_AUDIENCE`).
- Mobile may fall back to legacy password API when Auth0 env is absent; web may render without Auth0 in CI — **PARTIAL** for strict Auth0-only everywhere.

---

## Task 5 — MFA

| Item | Status |
| --- | --- |
| Auth0 tenant MFA policy | **UNVERIFIED** — not represented in repo |
| Docs | `docs/development/MFA_CONFIGURATION.md` — Post-Login Action example |
| API enforcement | `GET /api/v1/auth/staff-session` uses `get_staff_user` / `require_mfa` when flag true |
| Default local | `AUTH0_REQUIRE_MFA_CLAIM=false` in `apps/api/.env.example` |

**Verdict: UNVERIFIED** until staff login completes MFA in a real tenant and (optionally) `amr` contains `mfa` with flag enabled.

---

## Task 6 — Six Auth0 users

| Source | Content |
| --- | --- |
| Onboarding | `docs/development/FULL_AUTH_ONBOARDING.md` |
| Checklist | `docs/development/ROLE_ACCEPTANCE_CHECKLIST.csv` — rows R1–R6 unfilled |
| Bootstrap | `scripts/bootstrap-identity.ps1`, `apps/api/scripts/bootstrap_identity.py` |
| Email placeholders | `scripts/meeting-six-roles.env.example` (not credentials) |

**Verdict: UNVERIFIED** — needs `meeting-six-roles.local.env`, Auth0 users, `.\scripts\bootstrap-all-six-roles.ps1`, then checklist sign-off.

---

## Test evidence (auth-focused)

| Suite | Result |
| --- | --- |
| `tests/test_auth_tokens.py` | Passed (mocked JWKS) |
| `tests/test_auth_identity.py` | Passed |
| `tests/test_identity_bootstrap.py` | Passed |
| Full `apps/api` pytest | **415 passed**, 116 skipped, 0 failed (~36s) |
| `room-ready` Jest `tenantMobile` | **14 passed** |

---

## References

- Prior sprint: `docs/audit/PROMPT_1_TEST_REPORT.md`, `PROMPT_1_FIX_REPORT.md`
- Feature row snapshot: `docs/audit/FEATURE_56_STATUS.csv` (M01.1–M01.3)