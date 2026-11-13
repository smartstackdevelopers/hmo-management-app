# Production deployment approval gate

**Do not bypass.** Deployment proceeds only when **every mandatory row** is **PASS** or **APPROVED** and project owner signs below.

| # | Requirement | Status | Notes |
| --- | --- | --- | --- |
| 1 | AWS account access (operator) | **PENDING APPROVAL** | No deploy credentials in repo |
| 2 | Approved AWS region (target **eu-west-2**) | **PENDING APPROVAL** | Documented in F7.6 |
| 3 | Domain ownership | **PENDING APPROVAL** | `CONFIG_PLACEHOLDER` |
| 4 | SSL certificate (ACM on ALB) | **PENDING APPROVAL** | Requires live stack |
| 5 | Production env configuration | **PARTIAL** | Examples only — `production.env.example` patterns |
| 6 | Database readiness (RDS) | **BLOCKED** | Not provisioned |
| 7 | Redis readiness (ElastiCache) | **BLOCKED** | Not provisioned |
| 8 | S3 private buckets | **BLOCKED** | Not provisioned |
| 9 | Security approval | **PENDING APPROVAL** | F7.1 PARTIAL |
| 10 | Privacy / DPIA approval | **PENDING APPROVAL** | F7.2 PARTIAL |
| 11 | Backup verified before cutover | **BLOCKED** | No prod backup yet |
| 12 | Rollback plan acknowledged | **PASS** (documentation) | `docs/operations/infrastructure/ROLLBACK_PLAN.md` |
| 13 | F7.10 coverage acceptable to owner | **FAIL** | 55% strict PASS |
| 14 | **Project owner deployment approval** | **PENDING APPROVAL** | **Not evidenced in this session** |

## Sign-off block (complete externally)

| Role | Name | Signature / date | Approval |
| --- | --- | --- | --- |
| Project owner | **CONFIG_PLACEHOLDER** | | ☐ |
| Security lead | **CONFIG_PLACEHOLDER** | | ☐ |
| DPO / privacy | **CONFIG_PLACEHOLDER** | | ☐ |
| Technical lead | **CONFIG_PLACEHOLDER** | | ☐ |

## Gate outcome (this run)

| Overall | **BLOCKED** |
| --- | --- |
| Live changes made | **None** |
| Existing production services | **Unchanged** (none provisioned from HMore repo) |
