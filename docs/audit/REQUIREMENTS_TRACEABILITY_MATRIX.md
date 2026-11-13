# Requirements traceability matrix (summary)

**Full machine-readable matrix:** [REQUIREMENTS_TRACEABILITY_MATRIX.csv](./REQUIREMENTS_TRACEABILITY_MATRIX.csv) (**161** rows).

**Authoritative requirements text:** `docs/HMore-Proposal-Exact-Implementation-Plan-v1.0.md` Sections 3–7 (Proposal §§4–9).

## Row ID scheme

| Prefix | Scope |
| --- | --- |
| `S4-01-01` … `S4-14-04` | Proposal §4 — 14 platform modules (4 bullets each) |
| `S5-AGENT-01` … `06` | Six AI agents |
| `S5-SMART-*`, `S5-RAI-*`, `S5-COST-*` | §5 smart features, responsible AI, cost control |
| `S6-T-*`, `S6-S-*` | Proposal §6 mobile tenant/staff bullets |
| `S7-01` … `10` | Proposal §7 occupancy features |
| `S8-*` | Proposal §8 technology stack |
| `S9-*` | Proposal §9 security/compliance |
| `PH7-*` | Phase 7 go-live features F7.1–F7.10 |
| `F1.1` … `F6.7` | Delivery phase feature roll-ups |

## Status totals (mandatory denominator excludes **NOT SELECTED**)

| Status | Count |
| --- | ---: |
| PASS | 88 |
| IMPLEMENTED | 2 |
| PARTIAL | 65 |
| FORMALLY_DEFERRED | 4 |
| PENDING APPROVAL | 1 |
| NOT SELECTED | 1 |

## Columns in CSV

`requirement_id`, `proposal_section`, `module`, `requirement`, `status`, `evidence`, `remaining`

Each **PASS** row cites a test module, API area, or phase report. **PARTIAL** rows link to `MISSING_FEATURES_REGISTER.md`.

## Phase 6 spot-check (prompt §4)

| Feature | Status | Evidence |
| --- | --- | --- |
| F6.1 Landlord enterprise | PARTIAL | `test_f61_landlord_enterprise.py`, `/dashboard/landlord` |
| F6.2 Reports & analytics | PARTIAL | `test_f62_reports_analytics.py`, Celery beat `test_f68` |
| F6.3 Automation | PARTIAL | `test_f63_automation_rules.py` |
| F6.4 Integration hub | PARTIAL | `test_f64_integration_hub.py` |
| F6.5 Room occupancy | PARTIAL + **FORMALLY_DEFERRED** live | `test_f65_room_occupancy.py`, deferral doc |
| F6.6 Finance | **IMPLEMENTED** (client approved) | `test_f66_finance_module.py` |
| F6.7 Council portal | **IMPLEMENTED** (client approved) | `test_f67_council_portal.py` |

Do not treat optional Section 11 add-ons not purchased as mandatory failures (see [OPTIONAL_SCOPE_REGISTER.md](./OPTIONAL_SCOPE_REGISTER.md)).
