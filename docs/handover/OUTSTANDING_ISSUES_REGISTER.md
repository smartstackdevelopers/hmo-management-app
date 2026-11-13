# Final remediation register (release-blocking highlighted)

| ID | Phase | Feature | Severity | Description | Action | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ACC-01 | 7 | Production | **P0** | No production deploy | Approve gate + deploy | Client/platform | **BLOCKED** |
| ACC-02 | 7 | Coverage | **P0** | 55% strict PASS vs 100% exit | Close PARTIAL rows | Product | **OPEN** |
| ACC-03 | 1/7 | MFA | **P0** | MFA not enforced prod | Auth0 + env | IdP admin | **PENDING** |
| ACC-04 | 7 | Privacy | **P0** | No DPO/legal sign-off | External approval | DPO | **PENDING** |
| ACC-05 | 7 | Mobile | **P0** | Stores not LIVE | EAS submit | Mobile lead | **BLOCKED** |
| ACC-06 | 6 | Occupancy live | **P1** | Live counting deferred | Per-org DPIA gate | Org Admin | **DEFERRED** |
| ACC-07 | 7 | Training | **P1** | No delivery records | Run sessions | Client HR | **PENDING** |
| ACC-08 | 7 | DR | **P1** | No prod restore drill | Isolated drill | Ops | **OPEN** |
| ACC-09 | 7 | Security | **P2** | No pen test | Commission test | Security | **OPEN** |
| ACC-10 | 7 | A11y | **P2** | WCAG partial | F7.5 residuals | Web team | **OPEN** |

Post-launch improvements: see `docs/audit/REMEDIATION_PLAN.md` R14–R19.

**No code changes** made during F7.12 acceptance.
