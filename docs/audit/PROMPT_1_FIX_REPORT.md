# PROMPT 1 — Critical Fixes Sprint (Fix Report)

**Date:** 14 November 2026  
**Branch:** `fix/develop-ci-migration-downgrade` (includes PR #112 F8.11 downgrade CASCADE)  
**Scope:** Local development only — no production deploy.

## Issues addressed

| ID | Issue | Root cause |
|----|--------|------------|
| **M10.1** | Super Admin organisations page was an `EmptyState` stub | Web UI never called `GET /api/v1/platform-governance/platform/organisations` or `POST /api/v1/organisations` |
| **P7** | Mobile defaulted to legacy `http://<host>:3001` | `room-ready/lib/config.ts` used `EXPO_PUBLIC_API_URL ?? …:3001` |
| **Pytest** | `test_upgrade_downgrade_roundtrip` failed; RBAC registry teardown pollution | F1.5 migration tried `DROP ROLE hmore_app` while hundreds of grants still referenced the role; failed downgrade left session DB inconsistent |

## Fixes implemented

### Task 1 — Super Admin organisations UI

- Wired server page to Auth0 token + platform governance list API.
- Added client create form → existing `POST /api/v1/organisations`.
- Loading/error/empty states via server fetch + form client states.
- Reused `platform_governance.service.list_organisations` (no duplicate list API).

### Task 2 — Mobile port 3001

- HMore base URL remains `EXPO_PUBLIC_HMORE_API_URL` / port **8000** (`room-ready/lib/hmore/config.ts`).
- Removed silent **3001** default; legacy API requires explicit `EXPO_PUBLIC_API_URL` or throws `LegacyApiConfigurationError`.
- File URLs use HMore API origin, not legacy port.
- Docs/env example updated.

### Task 3 — Pytest / migrations

- F1.5 downgrade: stop dropping `hmore_app` role during full downgrade (revoke grants only); upgrade already uses `IF NOT EXISTS`.
- `test_db_schema.py`: ensure re-`upgrade` to `head` on roundtrip failure (session safety).
- F8.11 downgrade CASCADE retained (PR #112).

## Files modified / added

**Web**

- `apps/web/src/app/dashboard/super-admin/organisations/page.tsx`
- `apps/web/src/components/platform/CreateOrganisationForm.tsx` (new)
- `apps/web/src/components/platform/OrganisationsTable.tsx` (new)
- `apps/web/src/lib/organisationsApi.ts` (new)
- `apps/web/src/lib/platformGovernanceApi.ts`

**API / migrations / tests**

- `apps/api/migrations/versions/20261105_1700_f15_rls_app_role.py`
- `apps/api/tests/test_db_schema.py`
- `apps/api/tests/test_super_admin_organisations_api.py` (new)

**Mobile**

- `room-ready/lib/config.ts`
- `room-ready/lib/network.ts` (new)
- `room-ready/lib/legacyApiConfig.ts` (new)
- `room-ready/lib/hmore/config.ts`
- `room-ready/lib/api.ts`
- `room-ready/.env.example`
- `room-ready/__tests__/tenantMobile.test.ts`
- `docs/development/TENANT_MOBILE_SETUP.md`

## Task status (strict)

| Task | Status | Notes |
|------|--------|-------|
| M10.1 UI + API wiring | **PARTIAL** | Code + API tests pass; **Auth0 browser E2E not run** in this session |
| Mobile 3001 removal | **PASS** | No default 3001; Jest green |
| Pytest green | **PASS** | **530 passed** locally on `hmore_test` |

## M10.1 acceptance (honest)

| Criterion | Status |
|-----------|--------|
| Super Admin sees real org rows | **UNVERIFIED** in browser (needs live Auth0 + API) |
| Data from PostgreSQL via API | **PASS** in API integration tests |
| Create org | **PASS** in API tests |
| Unauthorized blocked | **PASS** (tenant → 403 on platform list) |
| `PLATFORM_GOVERNANCE_GLOBAL_ENABLED` | Must be `true` on API for list endpoint (documented in UI error copy) |