# PROMPT 12 — Native Auth Implementation Report

| Field | Value |
| --- | --- |
| Date | 2026-11-16 |
| Status | **PARTIAL** |
| Git | `develop` @ `a2fb515` + uncommitted Prompt 12 work |

## Summary

Native HMore authentication was implemented as the **active** application auth path:

- Email/password register + login
- Pending → approve/reject workflow
- In-app auth notifications
- Argon2id password hashing
- Short-lived access tokens + rotating refresh tokens
- Web login/register/logout + approvals UI
- Mobile native password login mode
- Auth0 JWT validation disabled unless `HMORE_ALLOW_AUTH0=true`

## Exact files modified / added (core)

### API
- `app/auth/passwords.py` *(new)*
- `app/auth/native_tokens.py` *(new)*
- `app/auth/native_service.py` *(new)*
- `app/api/v1/native_auth.py` *(new)*
- `app/api/v1/router.py`
- `app/auth/tokens.py`
- `app/auth/identity.py`
- `app/core/config.py`
- `app/db/models/user.py`
- `app/db/models/enums.py`
- `app/db/models/native_auth.py` *(new)*
- `app/db/models/__init__.py`
- `migrations/versions/20261124_6000_p12_native_auth.py` *(new)*
- `requirements.txt`
- `tests/test_p12_native_auth_unit.py` *(new)*
- `.env.example`

### Web
- `src/lib/nativeAuth.ts` *(new)*
- `src/lib/auth0.ts` (compat shim → native cookies)
- `src/lib/session.ts`
- `src/lib/rbac.ts` (`LOGIN_PATH=/login`)
- `src/lib/authRoutes.ts`
- `src/app/login/page.tsx` *(new)*
- `src/app/register/page.tsx` *(new)*
- `src/app/register/pending/page.tsx` *(new)*
- `src/app/auth/logout/route.ts` *(new)*
- `src/app/dashboard/approvals/registrations/*` *(new)*

### Mobile
- `lib/hmoreNativeAuth.ts` *(new)*
- `contexts/AuthContext.tsx`
- `app/(auth)/login.tsx`

## Database migrations

| Revision | Purpose | Applied locally? |
| --- | --- | --- |
| `20261124_6000_p12` | users password/status columns + registration/refresh/reset/notification/audit tables | **BLOCKED** — Postgres/Docker not reachable at runtime |

## API endpoints (native)

| Method | Path |
| --- | --- |
| POST | `/api/v1/auth/register` |
| POST | `/api/v1/auth/login` |
| POST | `/api/v1/auth/refresh` |
| POST | `/api/v1/auth/logout` |
| GET | `/api/v1/auth/registration-requests` |
| POST | `/api/v1/auth/registration-requests/{id}/approve` |
| POST | `/api/v1/auth/registration-requests/{id}/reject` |
| POST | `/api/v1/auth/users/organisation-admin` |
| PATCH | `/api/v1/auth/users/{id}/account-status` |
| POST | `/api/v1/auth/password/change` |
| POST | `/api/v1/auth/password/forgot` |
| POST | `/api/v1/auth/password/reset` |
| GET | `/api/v1/auth/notifications` |
| POST | `/api/v1/auth/notifications/{id}/read` |
| POST | `/api/v1/auth/bootstrap-super-admin` |

Demo endpoints remain for meeting use only (`HMORE_DEMO_AUTH`).

## Authentication flow

1. User registers → `account_status=pending` + `registration_requests` row  
2. Org Admin / Super Admin notified in-app  
3. Approve → membership granted + `account_status=approved`  
4. Login → Argon2 verify → access JWT + refresh row  
5. API validates native JWT first; Auth0 only if explicitly allowed  

## Role permissions

Unchanged six-role RBAC matrix. Registration policies:

- Public: landlord, tenant, support_worker, maintenance_contractor  
- Org Admin creation: Super Admin only  
- Super Admin: never self-register  

## Remaining

- Apply Alembic when Postgres is up  
- Full integration pytest against DB  
- CSRF cookie hardening polish for cookie-authenticated mutations (Bearer-primary today)  
- Remove unused `@auth0/nextjs-auth0` package after dashboard smoke  

## Status

**PARTIAL** — code complete for local architecture; DB migration + full E2E blocked without Postgres.
