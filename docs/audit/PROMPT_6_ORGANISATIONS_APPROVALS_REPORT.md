# PROMPT 6 — M10 Organisations & Approvals

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` (local, 4 commits ahead of `origin/develop`) |
| Scope | Local verification only — no production |

## Summary verdict

| ID | Feature | Status | Notes |
| --- | --- | --- | --- |
| **M10.1** | Super Admin organisations | **PARTIAL** | Prompt 1 wiring retained; platform list + create via `platformGovernanceApi` / `organisationsApi`; `PLATFORM_GOVERNANCE_GLOBAL_ENABLED` documented in UI |
| **M10.2** | Approvals inbox | **PARTIAL** | Web `org-workflows/approvals` → `listApprovalsInbox`; API `GET /api/v1/org-workflows/approvals/inbox`; no dedicated pytest for HTTP inbox (aggregation in `org_workflows.inbox`) |
| **M10.3** | Custom forms / workflows | **PARTIAL** | Web hub + `forms` / `workflows`; API F2.13; unit tests `test_f213_org_workflows.py` (schema + postgres isolation **skipped** — no DB) |
| **M10.4** | Secure sharing | **PARTIAL** | Web `org-workflows/sharing`; API grants; postgres test `test_f213_secure_sharing_revoke` **skipped** (no DB) |
| **M10.5** | Council Portal | **OPTIONAL** | `dashboard/council-portal` + `councilPortalApi` + `apps/api/app/api/v1/council_portal.py`; not expanded in this sprint |

**M10 mandatory completion (M10.1–M10.4):** **~75%** — code paths present; **LOCAL PASS** blocked by Auth0 browser E2E and offline Postgres integration tests.

## M10.1 — Reuse Prompt 1 (no duplicate APIs)

| Check | Result |
| --- | --- |
| `super-admin/organisations` loads from API | **PASS** (source) |
| `GET .../platform-governance/platform/organisations` | **PASS** (`test_f812_platform_governance.py` unit) |
| `POST /api/v1/organisations` super_admin | **SKIP** postgres (`test_super_admin_organisations_api.py` ×2) |
| Duplicate list API avoided | **PASS** — reuses `platform_governance.service.list_organisations` |

## M10.2–M10.4 — Web ↔ API

| Surface | Path | RBAC gate |
| --- | --- | --- |
| Inbox | `apps/web/.../org-workflows/approvals/page.tsx` | `approvals.inbox.read` |
| Hub | `org-workflows/page.tsx` | `approvals.inbox.read` \| workflow/form manage |
| Sharing | `org-workflows/sharing/page.tsx` | `secure_sharing.read` |
| API router | `apps/api/app/api/v1/org_workflows.py` | Org context + permissions |

## Tests executed (this session)

```powershell
cd apps\api
# DATABASE_URL unset — Postgres-marked tests auto-skipped
.\.venv\Scripts\pytest -q tests/test_f812_platform_governance.py tests/test_f213_org_workflows.py tests/test_super_admin_organisations_api.py
```

| File | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: |
| `test_f812_platform_governance.py` | 7 | 0 | 0 |
| `test_f213_org_workflows.py` | 2 | 2 | 0 |
| `test_super_admin_organisations_api.py` | 0 | 2 | 0 |

**Postgres retry:** Docker daemon **not running** → setting `TEST_DATABASE_URL` produced **15 errors** (connection refused); not counted as FAIL of application logic.

## Gaps

- Browser walkthrough: super_admin org list/create, org_admin approvals inbox with seeded pending items.
- HTTP-level approvals inbox assertion (optional future test).
- M10.2 mandatory LOCAL PASS per plan — treat as **PARTIAL** until Postgres + Auth0 demo.

## Out of scope (Task 10)

Finance payment gateway, contractor marketplace, integration hub — **not** mandatory M10 core.