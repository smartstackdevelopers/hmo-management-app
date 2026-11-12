# Phase 6 — Complete Integration & Feature Verification (Prompt 8)

**Plan:** HMore Proposal-Exact Complete Implementation Plan v1.0  
**Branch tip verified against:** `origin/develop` at `3532855` (F6.7 merge) plus integration fixes on this PR  
**Alembic head:** `20261111_4500_f67`  
**Date:** 2026-11-12  
**Scope:** Connect, check, verify F6.1–F6.7. No Phase 7 work. No fake integration successes.

Statuses used: **PASS** | **PARTIAL** | **FAIL** | **BLOCKED** | **NOT SELECTED**

---

## 1. Coverage summary

| ID | Feature | Status | Notes |
|----|---------|--------|-------|
| F6.1 | Landlord Enterprise Tools | **PARTIAL** | API + landlord UI + tests solid; org-admin read oversight fixed; write UI landlord-only; some CRUD UI gaps |
| F6.2 | Reports & Analytics | **PARTIAL** | Five categories, CSV/PDF/XLSX stream export, schedules, alerts, Celery beat; stored-export download UI + threshold edit UI thin |
| F6.3 | Automation Rules | **PARTIAL** | Rules/engine/escalations/compliance + Celery; not every trigger type has dedicated postgres coverage |
| F6.4 | Integration Hub | **PARTIAL** | Foundation PASS; generic REST adapters; partners **not connected** until real HTTPS test + credentials |
| F6.5 | Room Occupancy | **PASS** (module) / **BLOCKED** (live camera) | Privacy gate defaults `not_started`; no fake counts; live ingest disabled until DPIA gate complete |
| F6.6 | Finance & Budgets | **PASS** (approved add-on) | Client approved 2026-11-12; ledger + budgets; **no** payment gateways |
| F6.7 | Council Portal | **PASS** (approved add-on) / **PARTIAL** UX | Officers outside `HMoreRole` (still exactly 6); officer nav requires direct URL |

**Mandatory core exit:** F6.1–F6.5 implemented and wired. Remaining items are UI depth, operational DPIA, and live partner credentials — not missing modules.

---

## 2. F6.1 Landlord Enterprise — PARTIAL

**Verified present**
- API: `/api/v1/landlord-enterprise` — dashboard, portfolio, rent records, inspections, repairs
- Models/migration: `rent_records`, `property_inspections` (`20261111_3900_f61`)
- Ownership filter: landlords limited to `landlord_user_id` (or unassigned)
- Web: `/dashboard/landlord` calls live APIs (`landlordEnterpriseApi.ts`)
- Audit: rent create/status, inspection upsert
- Tests: `test_f61_landlord_enterprise.py`

**Bugs fixed this verification**
- Page previously used `requireDashboardRole("landlord")` while nav listed `organisation_admin` / `super_admin` → org admins hit `/unauthorized`. Now permission + role allow-list aligned with nav.
- Rent/inspection write controls hidden for non-landlord roles (matrix grants manage only to landlord).

**Remaining**
- Inspection update / rent archive APIs exist without matching UI.
- Portfolio `vacancy_trend` returned by API but not rendered.
- Super Admin lacks `properties.*` in matrix → cannot use F6.1 even if nav role list includes them (API-correct).

---

## 3. F6.2 Reports & Analytics — PARTIAL

**Verified present**
- Five categories: occupancy, housing, complaints, caseload, support-plan completion
- Date/org/property filters via reporting access layer
- Exports: CSV, PDF, Excel (stream) + secure stored download API
- Scheduled reports + Celery `hmore.reporting.dispatch_scheduled_reports` (300s)
- Early-warning alerts + Celery hourly evaluate
- Web panels: category pages, schedules, alerts
- Tests: `test_f62_reports_analytics.py`

**Remaining**
- No UI for stored scheduled-export download (`GET /reports/exports/{id}/download`)
- Alert threshold **edit** API not exposed in AlertsPanel (read + evaluate + status patch only)
- Nav previously omitted occupancy/plans/alerts/schedule/export perms — **fixed** this PR

---

## 4. F6.3 Automation Rules — PARTIAL

**Verified present**
- Rules CRUD, manual run, runs history, retry, escalations, compliance issues
- Engine + duplicate execution prevention patterns in postgres tests
- Celery `hmore.automation.dispatch_due_rules` every 300s (browser not required)
- Web: `/dashboard/automation`
- Tests: `test_f63_automation_rules.py`

**Remaining**
- Not every trigger/action key has a dedicated integration test
- Live Redis/Celery worker not exercised in this environment (registration verified)

---

## 5. F6.4 Integration Hub — PARTIAL

**Verified present**
- Registry, provider config, generic REST connectors, Fernet credential encryption
- Connection test → `connected` only after real HTTPS health check
- Sync jobs, activity logs, auto-sync Celery hourly
- Web dashboard uses live APIs; copy does not invent partner success
- Tests: `test_f64_integration_hub.py`

**Honest connection status**
- Council / HR / Finance / community-service adapters = **generic scaffolding**
- **No verified live partner connections** in this verification session
- Unconfigured integrations remain not connected by design

**Remaining**
- Field-mapping API helper exists; dashboard does not yet drive mapping UI

---

## 6. F6.5 Room Occupancy — PASS (module) / BLOCKED (live camera)

**Ten features (code)**
1. Live **estimated** occupancy fields (null when offline — not fake zeros)
2. Room dashboard UI + API
3. Camera/sensor counting via edge **ingest** only when gate allows
4. Five occupancy statuses
5. Capacity/equipment alerts + Celery sweep
6. History / usage report endpoints
7. Restricted access + access/audit paths
8. Last update, estimated labels, manual corrections with audit
9. Privacy/security controls (DPIA, feasibility, signage, retention, no facial recognition / identity / raw video defaults)
10. Web + Expo staff client paths for permitted users

**Approval / deferral**
- Gate defaults `not_started`; live ingest **403** until org completes approvals
- Operational live camera: **BLOCKED** pending DPIA / feasibility / signage (see `docs/operations/OCCUPANCY_FEASIBILITY_PACK.md`)
- **No synthetic occupancy generator**

**Remaining UI**
- Thin admin: limited gate notes PATCH; device/history/ack screens incomplete vs API surface

---

## 7. F6.6 Finance — PASS (Selected – Client Approved)

- **Not** “Not Selected” — chat approval recorded 2026-11-12 in `docs/F6.6-finance-module.md`
- Ledger + budgets + variance + exports; optional link to F6.1 `rent_records`
- Disclaimer + tests reject payment-gateway claims
- **No** Stripe/PayPal/open-banking product integration
- Web: `/dashboard/finance`
- Tests: `test_f66_finance_module.py`
- Nav perms expanded to include budgets/exports this PR

---

## 8. F6.7 Council Portal — PASS (Selected) / PARTIAL UX

- **Not** “Not Selected” — approved 2026-11-12 in `docs/F6.7-council-portal.md`
- Officers via `council_portal_officers` — **not** a seventh `HMoreRole`
- Core roles remain exactly **6** (`test_exactly_six_approved_roles`, `test_f67`)
- Share-scoped sanitized housing views + access logs
- Admin UI + officer inbox when URL known
- Nav visibility requires `council_portal.manage` (officers use direct URL) — documented limitation

---

## 9. Cross-module integration

| Link | Result |
|------|--------|
| Landlord portfolio ↔ F6.2 occupancy reports | Shared occupancy math / real property-room data |
| Rent records ↔ Finance outstanding | Finance reads landlord ledger; separate `finance_records` table (no duplicate rent rows) |
| Inspections ↔ maintenance repairs | Landlord repairs oversight reads maintenance tickets |
| Complaints ↔ automation escalations | Automation engine + complaint modules coexist; escalation lifecycle tested |
| Staff tasks ↔ automation reminders | Reminder/escalation action keys; Celery dispatch |
| Support plans ↔ plan-completion reports | F6.2 plans category |
| Occupancy ↔ analytics | F6.2 occupancy uses property occupancy; F6.5 IoT counts gated separately |
| Integration Hub ↔ background jobs | Celery auto-sync when `connected` + `auto_sync` |
| Notifications ↔ scheduled reports | F6.2 schedule jobs registered; delivery depends on communication stack config |
| Audit across F6.x | `record_event` in F6.1–F6.7 services; F6.2 audits exports/schedules/alerts (not every read) |

No duplicate Phase 6 routers. F1.10 occupancy surveys vs F6.5 room occupancy remain separate prefixes.

---

## 10. Database verification

| Check | Result |
|-------|--------|
| Migration chain F6.1→F6.7 | Linear; head `20261111_4500_f67` |
| Models | Distinct tables per feature; finance may FK rent |
| Destructive migrations | None run this session |
| Postgres isolation tests | Present; **ERROR** locally (Postgres not reachable on `127.0.0.1:5432`) — environment BLOCKED, not code FAIL |

---

## 11. API verification

| Prefix | Module |
|--------|--------|
| `/api/v1/landlord-enterprise` | F6.1 |
| `/api/v1/reports` | F6.2 |
| `/api/v1/automation` | F6.3 |
| `/api/v1/integrations` | F6.4 |
| `/api/v1/room-occupancy` | F6.5 |
| `/api/v1/finance` | F6.6 |
| `/api/v1/council-portal` | F6.7 |

Registered in `apps/api/app/api/v1/router.py`. Validation/org scoping in module `access.py` files. No conflicting duplicate prefixes found.

---

## 12. Security & permissions

| Check | Result |
|-------|--------|
| Six core roles | **PASS** |
| Backend enforcement | **PASS** (module access helpers; UI is not authoritative) |
| Org isolation | Covered in F6 postgres tests (when DB available) |
| Landlord property ownership | **PASS** |
| Financial access | Finance RBAC + tenant blocked |
| Occupancy access | Gate + `occupancy.*` permissions |
| Council seventh core role | **Absent** (add-on officer table) |
| Direct API without UI | Officer/admin routes rely on API auth, not frontend alone |

---

## 13. Frontend & mobile

| Check | Result |
|-------|--------|
| Phase 6 pages in Next production build | **PASS** (all listed routes compiled) |
| Nav links | **PASS** after perm list fix |
| Fake success buttons | Not found on Phase 6 dashboards reviewed |
| Expo room occupancy client | Present (`room-ready` staff occupancy service) — not re-run on device this session |
| Playwright E2E | Config present; **not run** this session (no dedicated Phase 6 E2E suite asserted) |

---

## 14–15. Tests

### Passed (this session)

| Suite | Result |
|-------|--------|
| F6.1–F6.7 unit + non-postgres tests + RBAC registry | **48 passed**, 7 postgres deselected (`-m "not postgres"`) |
| `test_f68_phase6_celery_beat.py` | Beat registration for F6.2–F6.5 jobs |
| Web `next build` | **PASS** (Auth0 dpopUtils warning only) |

### Failed / blocked

| Item | Result |
|------|--------|
| 7 Postgres integration tests | **BLOCKED** — local Postgres socket failure (Docker CLI unavailable) |
| Live Celery/Redis execution | **BLOCKED** — no broker in verification env (registration PASS) |
| Playwright Phase 6 journeys | **Not run** |
| Mobile device checks | **Not run** |

---

## 16. Bugs fixed (this verification)

1. **F6.1 page role gate** mismatched nav (org admin unauthorized) → authenticated session + allow-list + permissions.
2. **F6.1 write UX** showed rent/inspection actions to roles without manage perms → landlord-only write controls.
3. **Reports / finance / occupancy nav `anyOf`** incomplete → expanded to match API permission IDs.
4. **Phase 6 Celery beat smoke test** added to prevent silent schedule drift.

---

## 17. Remaining issues

1. Postgres + Redis unavailable in this agent environment → isolation/E2E job execution not re-proven live.
2. F6.2 stored-export download UI; alert threshold editor UI.
3. F6.4 field-mapping UI; no verified third-party partner connections.
4. F6.5 live camera **BLOCKED** on org DPIA gate; thin device/history admin UI.
5. F6.7 officer navigation discoverability.
6. Super Admin lacks `properties.*` → cannot open landlord enterprise (matrix design).
7. No dedicated web unit/Playwright suite for Phase 6 pages.

---

## 18. Production build status

| Artifact | Status |
|----------|--------|
| `apps/web` `next build` | **PASS** |
| API import + pytest offline | **PASS** |
| Full stack with Postgres/Redis/Celery | **BLOCKED** (environment) |

---

## Final decision

Phase 6 **mandatory modules (F6.1–F6.5) are implemented and integrated** in code with real APIs, migrations, RBAC, audit hooks, and Celery registration. Optional add-ons **F6.6 and F6.7 are Selected and implemented** without payment gateways and without a seventh core role.

**Do not claim full production exit complete** until: Postgres integration suite is green in CI/staging, Celery workers process at least one scheduled report + automation tick, and org DPIA approvals are recorded before any live occupancy counting.

**Phase 7:** not started.
