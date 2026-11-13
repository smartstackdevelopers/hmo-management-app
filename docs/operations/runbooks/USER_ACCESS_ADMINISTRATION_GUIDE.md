# User access administration guide

Auth provider: **Auth0**. Authorisation: **six HMore roles** only (`HMoreRole` in `apps/api/app/rbac`).

## Roles (do not add core roles)

1. Super Admin  
2. Organisation Admin  
3. Landlord  
4. Tenant  
5. Support Worker  
6. Maintenance & Contractors  

## User account creation

1. Create user in Auth0 (or federated IdP) — **organisation process**.
2. Create organisation membership via API/UI with correct `HMoreRole`.
3. Super Admin: platform-wide; others scoped to `organisation_id`.

Assignment rules: `apps/api/app/rbac/assignment.py` — only Super Admin creates Super Admin.

## User deactivation

- Set membership `inactive` / remove membership — preserves audit history **PENDING APPROVAL** retention policy.
- Disable Auth0 user for complete lockout.

## Password recovery

Handled in Auth0 Universal Login — support resets via IdP admin, not HMore database passwords.

## MFA support

- Enforced when `AUTH0_REQUIRE_MFA_CLAIM=true` and IdP issues MFA claim.
- Dev default may be off — production **PENDING APPROVAL** (F7.1).

Staff training: `docs/training/quick-reference/login-mfa.md`.

## Role assignment and permission changes

- Organisation Admin manages org roles within matrix limits.
- Changes audited in `audit_events`.
- **Never** grant Super Admin without platform policy.

## Organisation access

Users may hold multiple memberships; active org selected per session (`X-Organisation-Id` / UI switch).

## Contractor access

Maintenance & Contractors role — least privilege; time-bound membership **PENDING APPROVAL** process.

## Lost device response

1. User reports to Organisation Admin.
2. Revoke device sessions (F4.6 API).
3. Auth0 refresh token revocation **operator**.
4. If breach suspected → breach response plan.

## Remote session invalidation

- Device session revocation endpoints.
- Auth0 session revoke for staff accounts.

## Audit

Review access in dashboard audit logs (permission: audit read per role matrix).
