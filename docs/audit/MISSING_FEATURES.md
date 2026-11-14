# Missing features & gaps (local 100% audit)

Audit date: 2026-11-14. Derived from `FEATURE_56_STATUS.csv` and repository inspection.

## P0 — Blocks local 100% gate

| ID | Gap | Owner action |
| --- | --- | --- |
| **M10.1** | Super Admin org UI wired (Prompt 1) — **browser not verified** in Prompt 7 | Login super_admin; open `/dashboard/super-admin/organisations` |
| **P7** | Mobile **3001 default removed** in code — env must set HMore URL | Confirm `room-ready/.env` + Auth0 |
| **Pytest** | **117 skips** without Docker/`hmore_test` | Start Docker; full parity re-run |
| **Roles** | No evidence all **6 roles** logged in locally in this audit | Execute `ROLE_ACCEPTANCE_CHECKLIST.csv` |

## P1 — Mandatory modules not LOCAL PASS (backend exists)

| Module | Feature IDs | Missing for LOCAL PASS |
| --- | --- | --- |
| M01 | M01.2, M01.4–M01.6 | Auth0 logout/login proof; MFA policy; audit UI smoke |
| M03 | M03.1–M03.5 | Auth0 + landlord UI smoke; property/room CRUD on your machine |
| M04 | M04.1–M04.6 | Staff mobile Auth0 path; caseload/visits E2E |
| M08 | M08.1–M08.4 | Tenant repair → landlord → contractor E2E |
| M10 | M10.2–M10.5 | Org admin approvals/workflows with live org |

## P2 — Communication & providers (expected MOCK locally)

| ID | Gap | Staging fix |
| --- | --- | --- |
| M11.3 | SMS/email/push providers not configured | SMTP, FCM, Twilio credentials |
| M13.3 | Celery/Redis schedules | Run Redis; verify beat |
| M12.4 | E-sign provider depth | Provider contract |

## P3 — Deferred / optional by design

| ID | Note |
| --- | --- |
| M14.3 | Live camera occupancy — DPIA gate (acceptable DEFER) |
| M10.5 | Council portal — client add-on |
| Phase 8 dashboards | Voice, rent payments, LMS, etc. — optional; org context required |

## Placeholder / fake success patterns (inventory)

| Pattern | Examples |
| --- | --- |
| EmptyState when auth/org missing | Many dashboard pages without session |
| EmptyState “Organisation context required” | Most org-scoped pages without session |
| Integration **stub adapters** | `apps/api/app/integrations/connectors/adapters.py` |
| **501** paid provider | `digital_id_esign/service.py` |
| **test** comms adapter | `apps/api/app/core/config.py` (`provider: test`) |

## Cross-cutting fixes

1. Complete **Auth0 + bootstrap** for six emails (`FULL_AUTH_ONBOARDING.md`).
2. **Stop legacy demo API** in daily workflow.
3. **AI agents**: open each dashboard route once with valid token — confirm no 500.
4. **Production**: not in scope until local 100% gate + `DEPLOYMENT_APPROVAL_GATE.md`.