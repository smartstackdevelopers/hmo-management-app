# Final acceptance matrix (summary)

**Full row-level matrix:** `docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.csv` (161 rows).  
**This table:** phase/feature acceptance roll-up for sign-off meetings.

| Phase | Feature / area | Impl. | Test | Security | Privacy | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | RBAC six roles | PASS | PASS | PASS | N/A | **PASS** |
| 1 | Org isolation | PASS | PARTIAL | PASS | PASS | **PARTIAL** |
| 1 | MFA | PARTIAL | PARTIAL | PARTIAL | N/A | **PARTIAL** |
| 2 | Housing / support / repairs | PASS | PASS | PASS | PASS | **PASS** |
| 2 | Documents / comms | PARTIAL | PASS | PASS | PASS | **PARTIAL** |
| 3 | Six AI agents | PASS | PASS | PASS | PARTIAL | **PARTIAL** |
| 4 | Tenant mobile | PASS | PARTIAL | PARTIAL | PASS | **PARTIAL** |
| 4 | Staff mobile | PASS | PARTIAL | PARTIAL | PASS | **PARTIAL** |
| 5 | Community / jobs / wellbeing | PASS | PASS | PASS | PASS | **PASS** |
| 6 | Landlord enterprise | PARTIAL | PASS | PASS | N/A | **PARTIAL** |
| 6 | Reports / automation / integration | PARTIAL | PASS | PASS | N/A | **PARTIAL** |
| 6 | Room occupancy (module) | PARTIAL | PASS | PASS | PARTIAL | **PARTIAL** |
| 6 | Live occupancy ingest | DEFERRED | PASS deny | PASS | BLOCKED gate | **FORMALLY_DEFERRED** |
| 6 | Finance (approved) | IMPLEMENTED | PASS | PASS | N/A | **PASS** |
| 6 | Council portal (approved) | IMPLEMENTED | PASS | PASS | N/A | **PARTIAL** UX |
| 7 | Production LIVE | NOT DEPLOYED | NOT RUN | N/A | N/A | **BLOCKED** |
| 7 | Training delivered | N/A | N/A | N/A | N/A | **PENDING** |

## Major modules (Prompt §3)

| Module | Decision | Evidence |
| --- | --- | --- |
| Organisation / user management | **PASS** | Phase 1 APIs + web |
| Tenant / housing / property / room | **PASS** | `test_f16`, `test_f25` |
| Staff / support plans / notes | **PASS** | `test_f21`, `test_f210` |
| Maintenance / complaints / inspections | **PARTIAL** | `test_f28`, `test_f27`, `test_f61` |
| Documents / AI / reports / automation | **PARTIAL** | Phase 3 + F6 tests |
| Integration hub | **PARTIAL** | `test_f64` — no live partner |
| Mobile apps | **PARTIAL** | F7.7 — build prep not LIVE |
| Optional not selected (Sec 11) | **NOT SELECTED** | `OPTIONAL_SCOPE_REGISTER.md` |

Every **PASS** links to tests or reports named in the CSV `evidence` column.
