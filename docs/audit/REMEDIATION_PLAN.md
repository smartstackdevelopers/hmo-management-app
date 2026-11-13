# Remediation plan (post-audit)

**Scope:** Prioritised actions after F7.10. **No risky refactors during audit** — larger items are separate work packages.

## P1 — Go-live blockers

| # | Action | Owner | Depends on | Est. effort |
| --- | --- | --- | --- | --- |
| R1 | Client approve AWS Terraform apply (`stack_enabled=true`) | Client + platform | F7.6 | **PENDING APPROVAL** |
| R2 | Configure production Auth0 MFA + `AUTH0_REQUIRE_MFA_CLAIM=true` | IdP admin | F7.1 | **PENDING APPROVAL** |
| R3 | Complete organisational DPIA/privacy sign-off (F7.2) | DPO/client | Legal | **PENDING APPROVAL** |
| R4 | Occupancy: complete gate **per org** before live ingest OR maintain deferral | Org Admin | MF-02 | Per org |
| R5 | EAS production build + store submit (F7.7) | Mobile lead | Prod API URL | **PENDING APPROVAL** |
| R6 | Production secrets: S3 SSE, backup bucket, `INTEGRATION_SECRETS_KEY` | Platform | AWS | **PENDING APPROVAL** |

## P2 — Hardening & exit criteria

| # | Action | Evidence target |
| --- | --- | --- |
| R7 | Run staff training sessions; fill schedule template | F7.8 completion records |
| R8 | Production backup + isolated restore drill | F7.3 verified RPO/RTO |
| R9 | Close F7.5 accessibility residuals on priority dashboards | axe serious/critical = 0 |
| R10 | npm audit remediation plan (no blind major bumps) | F7.1 |
| R11 | Configure Sentry DSN + scrubbing + on-call routing | F7.6/F7.9 |
| R12 | Prove Celery/Redis in staging (scheduled reports, backups) | F6.2/F7.3 |
| R13 | Operational runbook sign-off | F7.9 approval |

## P3 — Incremental PARTIAL → PASS

| # | Action |
| --- | --- |
| R14 | Communication translation coverage review |
| R15 | Document e-sign UX depth vs Module 12 bullet |
| R16 | Integration hub live partner pilot (one council API) |
| R17 | Council portal officer nav discoverability |
| R18 | Reporting stored-export UI completeness |
| R19 | Regional rules configuration product design |

## Safe fixes allowed during audit

None applied in F7.10 (documentation-only phase).

## Tracking

Re-run coverage audit after remediation waves; update CSV statuses — target **100% PASS** on mandatory rows before claiming product exit.
