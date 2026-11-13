# Production readiness checklist

**Prepared:** 2026-11-12  
**Evidence rule:** Each item cites a report or artefact — not assumed from prior prompts.

| # | Check | Evidence reviewed | Result |
| --- | --- | --- | --- |
| 1 | Phase 6 exit | `docs/phase6/PHASE6_FINAL_EXIT_REPORT.md` | **PARTIAL** — code exit; occupancy live deferred |
| 2 | F7.1 security | `docs/phase7/F7.1_SECURITY_TESTING_REMEDIATION.md` | **PARTIAL** — no pen test; npm residuals |
| 3 | F7.2 GDPR/DPIA | `docs/phase7/F7.2_GDPR_DPIA_FINAL_REPORT.md` | **PARTIAL** — no legal/DPO sign-off |
| 4 | F7.3 backup/restore | `docs/phase7/F7.3_BACKUP_RESTORE_FINAL_REPORT.md` | **PARTIAL** — no prod RDS drill |
| 5 | F7.4 performance | `docs/phase7/F7.4_PERFORMANCE_FINAL_REPORT.md` | **PARTIAL** — benchmarks in app/CI |
| 6 | F7.5 accessibility | `docs/phase7/F7.5_ACCESSIBILITY_FINAL_REPORT.md` | **PARTIAL** — axe on critical paths |
| 7 | F7.6 AWS prep | `docs/phase7/F7.6_INFRASTRUCTURE_FINAL_REPORT.md` | **PARTIAL** — `stack_enabled=false` |
| 8 | F7.7 mobile | `docs/phase7/F7.7_MOBILE_RELEASE_FINAL_REPORT.md` | **PARTIAL** — not store LIVE |
| 9 | F7.8 training | `docs/phase7/F7.8_TRAINING_FINAL_REPORT.md` | **PARTIAL** — materials only |
| 10 | F7.9 runbooks | `docs/phase7/F7.9_RUNBOOKS_FINAL_REPORT.md` | **PARTIAL** — pending ops approval |
| 11 | F7.10 coverage | `docs/phase7/F7.10_FINAL_COVERAGE_REPORT.md` | **PASS** audit — **55%** strict PASS |
| 12 | CI green on `develop` | GitHub Actions | **PASS** (latest merged PRs) |
| 13 | Alembic migrations defined | `apps/api/migrations/` | **PASS** |
| 14 | Secrets not in Git | F7.1 + secrets hygiene CI | **PASS** |
| 15 | Proposal coverage ≥ 100% PASS | F7.10 matrix | **FAIL** — 55% |
| 16 | Project owner deploy approval | This gate | **PENDING APPROVAL** — not received |

## Gate decision

**Mandatory pre-deployment checks:** **FAIL**  
**Production deployment:** **BLOCKED** — do not apply Terraform, push ECS images to prod, or expose public endpoints.

Re-run this checklist after remediation (`docs/audit/REMEDIATION_PLAN.md` P1 items).
