# Missing features register (mandatory gaps)

Items where proposal core scope is **not PASS** or is **BLOCKED** / **FORMALLY_DEFERRED**. Optional Section 11 items are listed separately.

| ID | Requirement summary | Gap | Business impact | Technical impact | Priority |
| --- | --- | --- | --- | --- | --- |
| MF-01 | Production HMore live (Phase 7 exit) | No AWS apply; no prod URL | No public service | Infra not provisioned | **P1** |
| MF-02 | Live room people counting (§7) | **FORMALLY_DEFERRED** until DPIA gate | No live occupancy counts | Ingest 403 by design | **P1** (after legal) |
| MF-03 | Edge camera/RTSP integration | Not live | Cannot automate counts | Deferred with MF-02 | **P1** (after gate) |
| MF-04 | MFA enforced production staff | `AUTH0_REQUIRE_MFA_CLAIM` default off | Account takeover risk | IdP + env config | **P1** |
| MF-05 | iOS/Android store LIVE release | F7.7 prep only | Tenants/staff cannot install prod app | EAS submit blocked | **P1** |
| MF-06 | Staff training **delivered** | Materials only F7.8 | Operational misuse risk | Process not executed | **P2** |
| MF-07 | RPO/RTO verified DR drill prod | F7.3 partial | Recovery uncertainty | No prod drill evidence | **P2** |
| MF-08 | WCAG 2.2 AA all dashboards | F7.5 partial | Accessibility gaps | Residual axe findings | **P2** |
| MF-09 | Independent penetration test | F7.1 partial | Unknown vulns | npm transitive deps | **P2** |
| MF-10 | Production Sentry + alert routing | DSN pending | Slow incident detect | Monitoring incomplete | **P2** |
| MF-11 | Communication SMS/push prod | Channels PARTIAL | Missed alerts | Provider credentials | **P2** |
| MF-12 | GDPR/DPIA organisational sign-off | Templates only | Legal exposure | DPO approval external | **P1** |
| MF-13 | 100% mandatory PASS matrix | 65 PARTIAL rows | Exit checklist fail | Incremental hardening | **P2** |
| MF-14 | Configurable UK nation/council rules | Limited org settings | Regional compliance variance | Settings model shallow | **P3** |
| MF-15 | Full postgres isolation proof local | 110 postgres tests skipped locally | False confidence risk | CI provides evidence | **P3** |

**Not counted as mandatory failures:** Section 11 add-ons not selected (AI Voice Calling, Contractor Marketplace, etc.) — see OPTIONAL_SCOPE_REGISTER.
