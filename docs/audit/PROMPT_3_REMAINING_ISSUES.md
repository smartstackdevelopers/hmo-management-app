# PROMPT 3 — Remaining issues (post-implementation)

**Date:** 2026-11-14

---

## Verified LOCAL PASS (strict)

| Module | PASS | Total | % |
| --- | ---: | ---: | ---: |
| M02 | 4 | 4 | **100%** |
| M04 | 6 | 6 | **100%** |
| M05 | 2 | 2 | **100%** |
| **Combined** | 12 | 12 | **100%** (automated) |

---

## Still UNVERIFIED (not blockers for this sprint)

1. Auth0 live smoke — caseload, handover create, tenant needs edit on device.
2. M05.2 — download export PDF in browser after login.
3. Handover mobile UX — recipient picker depends on caseload assignments (manual UUID fallback remains).

---

## Out of scope

- Prompt 4, production deploy.
- Structured `tenant_needs_goals` timeline rows on tenant mobile (staff timeline API unchanged).

---

## Notes

- `tenants.needs_goals` is tenant-editable via `profile.update.own`; staff `notes` never exposed on `/tenant/me`.
- Mobile handovers use existing `POST /handovers` only; no RBAC bypass.