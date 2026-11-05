# Authorization Security (F1.4)

## Principles

- Deny-by-default
- Least privilege
- Server-side enforcement only for security decisions
- Trusted role source: PostgreSQL `organisation_memberships`
- Never trust client role claims, Auth0 custom claims for HMore roles, or request-body roles
- Never trust client-supplied organisation IDs as membership proof — headers may only select among assigned memberships

## Threat mitigations

| Threat | Mitigation |
| --- | --- |
| Vertical privilege escalation | Matrix denies admin permissions to lower roles; assignment API gated |
| Self-escalation to Super Admin | Only Super Admin may assign Super Admin; tenants lack `role_assignments.manage` |
| Horizontal IDOR (property/work order/caseload) | Resource helpers enforce ownership/assignment; full query isolation is F1.5 |
| Client-supplied role spoofing | Headers validated against DB memberships |
| Stale authorization after role change | `users.authorization_version` incremented; clients refresh `/api/v1/rbac/me` |
| Unprotected routes | New protected probes use `require_perm` / authz context; health remains public |
| Secrets in logs | Session tokens are not logged by RBAC modules |

## HTTP semantics

| Condition | Status |
| --- | --- |
| Missing/invalid/expired access token | 401 |
| Authenticated, no permission / bad membership selection | 403 |
| Invalid assignment payload (unknown role, bad org scope) | 400 |

## Role assignment rules

1. Roles must be one of the six `HMoreRole` values.
2. Super Admin membership: `organisation_id` must be null.
3. Other roles: `organisation_id` required.
4. Organisation Admin cannot assign Super Admin or cross-org memberships.
5. No anonymous or unauthenticated assignment endpoint.

## Assumptions

- Auth0 correctly issues and signs access tokens (F1.3).
- Access-token lifetime is short enough that revocation of refresh tokens plus expiry is acceptable (see Session Control).
- F1.5 will apply organisation filters on all data queries; F1.4 helpers are not a complete isolation layer.

## Known limitations

- Not a production security certification.
- Work-order and support-assignment entities are not fully modeled until later features; helpers accept IDs for enforcement contracts.
- Auth0 access tokens cannot be forcibly revoked mid-lifetime without Auth0 features / short TTL.
- Frontend `PermissionGate` is UX only.

## Review checklist used for F1.4

- [x] Deny-by-default matrix
- [x] No wildcard permissions
- [x] Assignment restricted
- [x] 401/403 consistency on RBAC routes
- [x] No secrets committed
- [ ] Full org isolation on every query (deferred to F1.5)
