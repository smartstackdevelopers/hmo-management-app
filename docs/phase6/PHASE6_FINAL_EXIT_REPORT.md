# Phase 6 — Final Testing, Security Audit & Exit Report (Prompt 9)

**Plan:** HMore Proposal-Exact Complete Implementation Plan v1.0  
**Audit date:** 2026-11-12  
**Codebase tip (pre-exit-fixes):** `origin/develop` @ `b335ff7`  
**Exit work branch:** `audit/phase6-exit-final`  
**Alembic head:** `20261111_4500_f67`  
**Phase 7:** **Not started**

Statuses: **PASS** | **FAIL** | **PARTIAL** | **BLOCKED** | **NOT SELECTED** | **FORMALLY DEFERRED**

---

## 1. Executive summary

Phase 6 **mandatory modules (F6.1–F6.5)** are implemented end-to-end (API, migrations, RBAC, web, Celery registration). Optional add-ons **F6.6 Finance** and **F6.7 Council Portal** are **client-approved** and implemented without payment gateways and without a seventh core role.

**Phase 6 exit decision: CONDITIONAL / NOT FULLY COMPLETE for production sign-off.**

Mandatory proposal exit items:

| # | Exit requirement | Verdict |
|---|------------------|---------|
| 1 | Analytics exports + scheduled reports live | **PARTIAL** — code + beat registered; runtime worker delivery not proven in this environment |
| 2 | Landlord enterprise views complete for core scope | **PARTIAL** — core landlord path verified; remaining UI depth gaps |
| 3 | Occupancy under DPIA **or** formally deferred | **FORMALLY DEFERRED** — written gate + `docs/phase6/F6.5_OCCUPANCY_FORMAL_DEFERRAL.md`; live ingest blocked |
| 4 | No Council Portal unless contracted | **PASS** — built after client approval (F6.7 selected) |

**Do not declare Phase 6 COMPLETE for production** until Postgres integration suite + Celery workers are green in staging and operators set `AUTH0_REQUIRE_MFA_CLAIM` + `INTEGRATION_SECRETS_KEY`.

Code-level Phase 6 delivery for F6.1–F6.7 is **present and audited**; remaining work is operational hardening and UI depth (listed below).

---

## 2–8. Feature statuses

### F6.1 Landlord Enterprise — **PARTIAL**
- Backend/API/DB: present (`/landlord-enterprise`, migration `f61`)
- Frontend: `/dashboard/landlord` live APIs
- Permissions: landlord ownership filter tightened (no unassigned leak); support worker / contractor **denied** F6.1 reads (security fix)
- Tests: `test_f61_landlord_enterprise.py`

### F6.2 Reports & Analytics — **PARTIAL**
- Five categories, CSV/PDF/XLSX stream export, schedules, early-warning alerts
- Celery: `hmore.reporting.dispatch_scheduled_reports`, `dispatch_early_warning_alerts`
- Gaps: stored-export download UI; threshold edit UI; live worker not exercised here

### F6.3 Automation Rules — **PARTIAL**
- Rules, runs, retry, escalations, compliance; Celery `dispatch_due_rules`
- Escalation status changes now audited (`automation.escalation.status`)
- Gaps: not every trigger type covered by dedicated tests; Redis runtime not proven here

### F6.4 Integration Hub — **PARTIAL**
- Registry, Fernet credentials, connection test honesty, sync framework, Celery auto-sync
- SSRF: private/metadata hosts blocked on `api_base_url`
- Prod: `INTEGRATION_SECRETS_KEY` required
- **No verified live partner connections** — unconfigured = not connected

### F6.5 Room Occupancy — **PARTIAL** (module) + **FORMALLY DEFERRED** (live camera)
- Ten proposal surfaces largely in code; defaults `not_started`; ingest **403** until gate
- Formal deferral: `docs/phase6/F6.5_OCCUPANCY_FORMAL_DEFERRAL.md`
- No fake occupancy data

### F6.6 Finance — **PASS** (Selected – Client Approved)
- Ledger/budgets/exports; no payment gateways; supporting file ID validated against org + `files.*`

### F6.7 Council Portal — **PASS** (Selected) / **PARTIAL** UX
- Officers outside `HMoreRole`; exactly **6** core roles
- Officer nav discoverability remains limited (`council_portal.manage` only)

---

## 9. Security audit findings

| Sev | Finding | Disposition |
|-----|---------|-------------|
| HIGH | F6.1 read via `properties.read` for support worker/contractor | **Fixed** — role allow-list |
| HIGH | Landlords saw unassigned properties | **Fixed** — own properties only |
| HIGH | Integration Fernet key optional in production | **Fixed** — `INTEGRATION_SECRETS_KEY` required |
| HIGH | F6.4 SSRF via private `api_base_url` | **Fixed** — host blocklist |
| HIGH | MFA claim default off | **Documented residual** — enable `AUTH0_REQUIRE_MFA_CLAIM=true` in production (Auth0 policy operator-owned) |
| MEDIUM | Finance `supporting_file_id` unchecked | **Fixed** |
| MEDIUM | Escalation status unaudited | **Fixed** |
| MEDIUM | No app-level rate limits on F6 routes | **Residual** — edge/WAF recommended |
| MEDIUM | Integration `last_error` may echo upstream | **Residual** |
| MEDIUM | Occupancy ingest uses user token not device HMAC | **Residual** (acceptable while live counting deferred) |
| INFO | No `dangerouslySetInnerHTML` in Phase 6 web | OK |
| INFO | SQLAlchemy bound params; no Phase 6 SQLi found | OK |
| INFO | Bearer API → low classic CSRF | OK |
| INFO | No committed `.env` secrets | OK |

---

## 10. Six-role permission audit

| Role | Verified |
|------|----------|
| Super Admin | Platform perms; F6.1 read allowed with org context after fix |
| Organisation Admin | F6.2–F6.7 manage/read per matrix; F6.1 oversight (no rent write) |
| Landlord | F6.1 write + ownership scope; finance read |
| Tenant | Denied finance/landlord enterprise/integrations |
| Support Worker | Denied F6.1 enterprise; partial reports/automation/occupancy read |
| Maintenance & Contractors | Denied F6.1 enterprise; property maintenance perms only |

**Seventh core role:** **Absent** (council officer is add-on table).

---

## 11. Database audit

- Linear migrations `f61`→`f67`; head `20261111_4500_f67`
- Org-scoped models + RLS on F6.3–F6.7 tables
- No destructive migrations run
- Postgres isolation tests **environment-blocked** locally (no Docker/Postgres)

---

## 12. API audit

All Phase 6 prefixes registered under `/api/v1`. Service-layer permission checks present. Fake success responses not found on audited paths. Writes use DB + audit where required (escalation status added).

---

## 13. Frontend & mobile audit

| Surface | Status |
|---------|--------|
| Next.js Phase 6 dashboards | Present; `next build` PASS (prior Prompt 8 + this branch) |
| Navigation permission lists | Aligned in Prompt 8 |
| Non-working controls | Landlord write gated for non-landlord; remaining thin UIs documented |
| Expo occupancy | Client present; device E2E **not run** |
| Playwright Phase 6 | **Not run** this session |

---

## 14. Background jobs audit

| Beat task | Registered |
|-----------|------------|
| `hmore.reporting.dispatch_scheduled_reports` | Yes |
| `hmore.reporting.dispatch_early_warning_alerts` | Yes |
| `hmore.automation.dispatch_due_rules` | Yes |
| `hmore.integrations.dispatch_auto_sync` | Yes |
| `hmore.room_occupancy.sweep` | Yes |

Evidence: `celery_app.py` + `test_f68_phase6_celery_beat.py`.  
**Runtime Redis/Celery execution:** **BLOCKED** (no broker in audit env). Jobs do not require a browser when workers run.

---

## 15–16. Tests

### Passed (this exit session)
```
60 passed, 7 deselected (pytest -m "not postgres")
```
Suites: `test_f61`–`test_f68`, `test_rbac_registry`, `test_f111_security_config`  
(Includes new F6.1 role-deny tests, F6.4 SSRF URL tests, production `INTEGRATION_SECRETS_KEY` assertion.)

### Failed / blocked
| Item | Status |
|------|--------|
| 7× `@pytest.mark.postgres` F6 isolation tests | **BLOCKED** — Postgres unavailable (deselected, not hidden) |
| Playwright E2E | **Not run** |
| Live Celery/Redis | **BLOCKED** |
| Mobile device | **Not run** |

---

## 17. Bugs fixed (Prompt 9)

1. F6.1 API overreach for support worker / maintenance contractor  
2. Landlord access to unassigned properties  
3. Production requires `INTEGRATION_SECRETS_KEY`  
4. Integration `api_base_url` SSRF hardening  
5. Finance supporting file org + files RBAC validation  
6. Automation escalation status audit event  
7. Formal F6.5 live-occupancy deferral document  

---

## 18. Remaining risks

1. MFA not enforced by default on Phase 6 org APIs  
2. No per-route rate limiting  
3. F6.4 partner connectors remain generic until real credentials + HTTPS success  
4. Postgres/Celery not re-proven in this workstation  
5. UI depth: stored exports, alert thresholds, integration mappings, occupancy admin, council officer nav  
6. Access tokens still passed into some client components (XSS amplification risk)

---

## 19. Production build status

| Check | Status |
|-------|--------|
| API offline pytest (Phase 6 relevant) | **60 passed**, 7 postgres deselected |
| Web `next build` | Unchanged this PR (API/docs/security only); Prompt 8 build was PASS |
| Full stack staging | **Not verified** |

---

## 20. Phase 6 exit checklist

| Requirement | Result |
|-------------|--------|
| Analytics exports + scheduled reports live | **PARTIAL** |
| Landlord enterprise core complete | **PARTIAL** |
| Occupancy DPIA Go **or** formal deferral | **FORMALLY DEFERRED** (written) |
| Council Portal only if contracted | **PASS** (approved add-on) |
| Six-role model intact | **PASS** |
| Org isolation enforced in code | **PASS** (postgres tests blocked locally) |
| Phase 1–5 not removed | **PASS** (no removals in exit fixes) |
| Phase 7 not started | **PASS** |

### Final declaration

**Phase 6 is NOT declared COMPLETE for production exit.**

**Phase 6 is code-complete for mandatory modules + approved add-ons**, with live occupancy **formally deferred**, subject to residual security/ops items above.

---

## 21. Final coverage matrix

| ID | Feature | Impl | Backend | Frontend | DB | Perms | Tests | Remaining | Evidence |
|----|---------|------|---------|----------|----|-------|-------|-----------|----------|
| F6.1 | Landlord Enterprise | PARTIAL | PASS | PARTIAL | PASS | PASS* | PARTIAL | UI CRUD depth; postgres blocked | `landlord_enterprise/*`, `test_f61*` |
| F6.2 | Reports & Analytics | PARTIAL | PASS | PARTIAL | PASS | PASS | PARTIAL | Stored export UI; worker runtime | `reporting/*`, `test_f62*` |
| F6.3 | Automation Rules | PARTIAL | PASS | PARTIAL | PASS | PASS | PARTIAL | Trigger breadth; Redis runtime | `automation/*`, `test_f63*` |
| F6.4 | Integration Hub | PARTIAL | PASS | PARTIAL | PASS | PASS | PARTIAL | No live partners; mapping UI | `integrations/*`, `test_f64*` |
| F6.5 | Room Occupancy | PARTIAL + **FORMALLY DEFERRED** | PASS | PARTIAL | PASS | PASS | PARTIAL | Live camera until DPIA | `room_occupancy/*`, F6.5 deferral doc |
| F6.6 | Finance | PASS | PASS | PARTIAL | PASS | PASS | PARTIAL | Void/PATCH UI depth | `finance/*`, `test_f66*` |
| F6.7 | Council Portal | PASS / PARTIAL UX | PASS | PARTIAL | PASS | PASS | PARTIAL | Officer nav | `council_portal/*`, `test_f67*` |

\*After Prompt 9 security fixes.

---

## Separated: verified vs unverified

| Verified in this audit | Not verified here |
|------------------------|-------------------|
| Source code, routers, migrations, RBAC matrix, Celery registration, offline unit tests, security code fixes | Live Postgres isolation, Celery worker ticks, Auth0 MFA tenant policy, AWS encryption-at-rest, Playwright, Expo device, real partner HTTPS connections |
