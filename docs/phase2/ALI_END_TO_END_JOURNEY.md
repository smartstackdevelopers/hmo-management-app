# F2.15 — Ali end-to-end journey (no AI automation)

## Authoritative scenario

From **HMore Proposal-Exact Implementation Plan v1.0 — F2.15**:

> Ali end-to-end journey without AI automation (**manual note → repair → admin → maintenance**)

Prototype persona **Ali Hassan** is represented using **synthetic test data only** (no real PII).

## Human workflow sequence

| Step | Role | Module | Action |
|------|------|--------|--------|
| 1 | Organisation Admin | F2.1 | Assign Support Worker to tenant caseload |
| 2 | Support Worker | F2.1 | Daily log: water leak under sink (staff-written) |
| 3 | Support Worker | F2.8 | Maintenance request with `requires_approval` |
| 4 | Organisation Admin | F2.8 / F2.13 | Approve maintenance in `awaiting_approval` |
| 5 | Organisation Admin | F2.13 | Approvals inbox aggregation (maintenance source) |
| 6 | Organisation Admin | F2.14 | Operational reporting dashboard |

**No AI agents, LangGraph, or autonomous decisions** are used in this journey.

## Reproduce in development

### Automated (PostgreSQL required)

```bash
cd apps/api
export TEST_DATABASE_URL=postgresql+psycopg://...
pytest tests/test_f215_ali_end_to_end.py -m postgres -v
```

### Manual UI (Auth0 + API running)

1. Create or open synthetic tenant record.
2. Assign caseload (`/dashboard/case-assignments`).
3. Add daily log (`/dashboard/support-worker`).
4. Create maintenance with approval required (`/dashboard/maintenance`).
5. Approve as Organisation Admin (maintenance UI or `/dashboard/org-workflows/approvals`).
6. Confirm metrics on `/dashboard/reports`.

### Playwright smoke (routes only)

```bash
cd apps/web
npx playwright test e2e/ali-journey.spec.ts
```

## Code references

- Step catalog: `apps/api/app/journeys/ali.py`
- Integration test: `apps/api/tests/test_f215_ali_end_to_end.py`
