# Multi-Tenant Security (F1.5)

## Controls

| Control | Status |
| --- | --- |
| Server-side membership validation | Implemented |
| Deny-by-default cross-org access | Implemented |
| Trusted organisation context dependency | Implemented |
| Application query scoping | Implemented |
| PostgreSQL FORCE RLS on org-owned tables | Implemented |
| Transaction-scoped SET LOCAL (no pool leak) | Implemented |
| Explicit Super Admin platform bypass | Implemented (`get_platform_context`) |
| Background job org payload validation | Foundation implemented |
| Frontend-only filtering | Not relied upon |

## Threats addressed

- Cross-tenant data leakage via list/get/update/delete
- IDOR by swapping record UUIDs
- Organisation ID header spoofing without membership
- Unauthorized membership self-activation
- Inactive/suspended membership reuse
- Accidental Super Admin unrestricted tenant endpoints
- Job payload org spoofing (when actor is supplied)

## Error behaviour

Cross-organisation access returns HTTP 403 with a generic "Access denied" style message. Responses must not confirm whether a foreign record exists.

## Not claimed

- UK GDPR certification
- Complete product CRUD coverage (F1.6+)
- Perfect security without operational review

## Residual risks

- Direct DB access with a superuser role outside the app bypasses RLS
- Code paths that forget `get_organisation_context` and also forget filters remain a risk — reviews and tests must catch new endpoints
- `session.get` after prior load may serve identity-map rows; helpers still compare `organisation_id`
