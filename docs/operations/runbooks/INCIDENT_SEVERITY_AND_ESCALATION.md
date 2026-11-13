# Incident severity and escalation

**Response time targets:** **PENDING APPROVAL** — do not treat tables below as contractual SLAs until signed.

## Severity definitions

| Severity | Impact | Examples |
| --- | --- | --- |
| **Critical** | Total loss of core service for all users; active data breach; DB corruption risk | API + web down; confirmed unauthorised bulk export |
| **High** | Major feature unavailable for many users; security control failure | Auth down; backups failing 24h+; AI down for all orgs |
| **Medium** | Limited users or single module; workaround exists | Single org misconfiguration; slow reports; one Celery queue stuck |
| **Low** | Cosmetic, single user, dev/staging only | UI glitch; one failed push; non-prod |

## Per-severity expectations

| Severity | Priority | Initial response | Escalation | Communication |
| --- | --- | --- | --- | --- |
| Critical | P1 | **PENDING APPROVAL** | Tech lead + **CONFIG_PLACEHOLDER — Management** | External comms **requires approval** |
| High | P2 | **PENDING APPROVAL** | Technical on-call → security if applicable | Internal status updates |
| Medium | P3 | **PENDING APPROVAL** | Team queue | Optional user notice |
| Low | P4 | Next business day | None | None |

## Escalation paths

### Technical incidents

1. Operator diagnoses via [APPLICATION_OPERATIONS.md](./APPLICATION_OPERATIONS.md).
2. Escalate **CONFIG_PLACEHOLDER — Technical on-call** if unresolved within **PENDING APPROVAL** window.
3. Database/AWS: [DATABASE_OPERATIONS_GUIDE.md](./DATABASE_OPERATIONS_GUIDE.md), [AWS_INFRASTRUCTURE_OPERATIONS_GUIDE.md](./AWS_INFRASTRUCTURE_OPERATIONS_GUIDE.md).

### Security incidents

→ [SECURITY_INCIDENT_RESPONSE_PLAN.md](./SECURITY_INCIDENT_RESPONSE_PLAN.md)  
Notify **CONFIG_PLACEHOLDER — Security lead** and **CONFIG_PLACEHOLDER — DPO** when personal data may be involved.

### Personal data breaches

→ [PERSONAL_DATA_BREACH_RESPONSE_PLAN.md](./PERSONAL_DATA_BREACH_RESPONSE_PLAN.md)  
**No automatic ICO notification** — DPO/legal assessment required.

### Database failures

Primary: DBA / technical on-call.  
If restore needed: [DISASTER_RECOVERY_RUNBOOK.md](./DISASTER_RECOVERY_RUNBOOK.md) with management approval.

### AWS infrastructure (when live)

CloudWatch alarms (when configured) → **CONFIG_PLACEHOLDER — Platform**.  
Terraform state changes require human `terraform apply` approval (F7.6).

### AI outages

Check AI service health, provider status, token and caps.  
Human approval workflows remain paused until service restored — staff use manual process.

### Mobile failures

Distinguish store/client vs API. Escalate to mobile build owner if crash regression after release.

### Tenant-facing interruption

Organisation Admin / comms lead drafts message — **external approval required**.

## Internal notification process

1. Open incident record (ticketing system **CONFIG_PLACEHOLDER**).
2. Assign severity and owner.
3. Time-stamped status updates at interval **PENDING APPROVAL**.
4. Post-incident review for Critical/High within **PENDING APPROVAL** days.

## Required approvals

| Action | Approval |
| --- | --- |
| Production deploy / rollback | **PENDING APPROVAL** — authorised release manager |
| Database restore to production | **PENDING APPROVAL** — management + DBA |
| External breach notification | **PENDING APPROVAL** — DPO/legal |
| Room occupancy live enable | **PENDING APPROVAL** — privacy gate in product |
| Destructive infra change | **PENDING APPROVAL** — client + technical lead |
