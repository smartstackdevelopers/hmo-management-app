# Audit log security (F1.7)

## Threat model (Phase 1)

- Clients must not invent actor identity or write arbitrary audit rows.
- Ordinary roles must not read other organisations’ audit trails.
- Audit rows must not store credentials (passwords, tokens, MFA codes, session secrets).
- Emergency-access audit events must not become an RBAC bypass.

## Controls

1. **Write path**: only `app.audit.service.record_event` (and CRUD/emergency callers). No public POST for audit events.
2. **Read path**: `audit_logs.read` + organisation context; platform list requires Super Admin bypass.
3. **Redaction**: metadata key substring matching for secrets; size cap 4096 bytes.
4. **DB privileges**: `hmore_app` has `SELECT, INSERT` only on `audit_events` (no `UPDATE`/`DELETE`).
5. **RLS**: `FORCE ROW LEVEL SECURITY` on `audit_events` with org match or `app.rls_bypass`.
6. **Emergency**: grant rows + audits only; API documents `grants_permissions: false`.

## Limitations (honest)

- Not tamper-proof: database owners / superusers can still modify rows.
- Auth0 login outcomes are primarily IdP-side; API logs invalid tokens, MFA denials, and permission denials.
- Retention period is unspecified (policy decision pending).
