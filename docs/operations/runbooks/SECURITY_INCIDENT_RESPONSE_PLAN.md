# Security incident response plan

**Status:** Prepared — adoption and drills **PENDING APPROVAL**. This is not evidence that a drill has been run.

Aligns with F7.1 findings (`docs/phase7/F7.1_SECURITY_TESTING_REMEDIATION.md`). HMore provides audit logs, RBAC, and session revocation — not autonomous breach detection.

## Stages

| Stage | Activities | Owner |
| --- | --- | --- |
| 1. Preparation | Runbooks, access controls, backup verification, MFA policy | **CONFIG_PLACEHOLDER — Security / Platform** |
| 2. Detection | Sentry alerts, failed auth spikes, staff reports, AWS/Auth0 logs | Operators + monitoring |
| 3. Initial assessment | Severity → [INCIDENT_SEVERITY_AND_ESCALATION.md](./INCIDENT_SEVERITY_AND_ESCALATION.md) | Incident commander **PENDING APPROVAL** |
| 4. Containment | Revoke credentials, invalidate sessions, block IP at WAF **if configured** | Technical team |
| 5. Investigation | Preserve `audit_events`, logs, backup manifests; timeline | Technical + **CONFIG_PLACEHOLDER — Security** |
| 6. Eradication | Patch, rotate secrets, remove malicious access | Technical team |
| 7. Recovery | Restore service; validate integrity | Technical team |
| 8. Post-incident review | Lessons, F7.1 residual updates, training pointers | Management |

## Scenario playbooks

### Unauthorised account access

1. Identify Auth0 subject / membership IDs from audit logs.
2. Organisation Admin or Super Admin disables user / membership.
3. `POST` device session revocation (F4.6) where applicable.
4. Force password reset via Auth0 policy — **operator action**.

### Suspected credential theft

1. Rotate affected secrets (API, integration Fernet key per runbook — **requires approval**).
2. Invalidate all active sessions for impacted users.
3. Review `audit_events` for exfiltration patterns.

### Data exposure (non-breach vs breach)

- If personal data involved → switch to [PERSONAL_DATA_BREACH_RESPONSE_PLAN.md](./PERSONAL_DATA_BREACH_RESPONSE_PLAN.md).
- If configuration only → document under security incident, lower severity.

### Malware on operator workstation

Out of band — isolate device; no HMore-specific automation. Lost device → USER_ACCESS guide.

### API attacks (abuse, injection attempts)

1. Rate limiting / WAF **PENDING APPROVAL** at edge.
2. Review API logs; block source if confirmed malicious.
3. Confirm parameterised queries and file validation (F7.1 PASS for design).

### Database compromise suspicion

1. **Do not** destroy evidence.
2. Snapshot RDS (when AWS live) — **PENDING APPROVAL**.
3. Isolate credentials; forensic restore to **separate** instance only (`DATABASE_RESTORE_PROCEDURE.md`).

### File storage exposure

1. Verify bucket policy private + SSE.
2. List affected object keys from audit; revoke presigned patterns if any misconfiguration.
3. Notify DPO if personal documents affected.

### Lost or stolen mobile device

Tenant/staff: remote session revoke; Org comms to user. See user access guide.

### Privilege escalation

1. Freeze role assignment changes for affected org.
2. Review `audit_events` for `role` / `permission` changes.
3. Revert membership to last known good **with approval**.

### Suspicious AI activity

1. Disable org AI flags if urgent (`org AI feature flags`).
2. Review AI activity logs / usage dashboard.
3. Check for abnormal export of case notes — treat as potential data incident.

## Evidence preservation

- Export relevant `audit_events` (read-only query).
- Preserve Sentry issue IDs and log stream pointers.
- **Do not** delete production rows for convenience.

## Communication

- Internal: incident channel **CONFIG_PLACEHOLDER**.
- External / regulators: **only after DPO/legal approval** (breach plan).
- Tenants: Organisation-led messaging.

## Post-incident

- Update `docs/security/` checklists if gaps found.
- Link to safeguarding/incident module in app when appropriate.
- **Do not** claim certification or pen-test pass from this document alone.
