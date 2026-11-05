# Core Records Architecture (F1.6)

## Entities

| Record | Table | Org scoped | Notes |
| --- | --- | --- | --- |
| Tenant person | `tenants` | Yes | Not the Tenant login role |
| Property | `properties` | Yes | Optional `landlord_user_id` |
| Room | `rooms` | Yes | Must match parent property org |

## Relationships

```text
Organisation 1──* Tenant
Organisation 1──* Property 1──* Room
User (optional) 1──* Tenant.user_id
User (optional) 1──* Property.landlord_user_id
```

## Isolation and RBAC

- All routes use `get_organisation_context` + F1.4 `require_perm`.
- Creates always stamp `organisation_id` from trusted context.
- Rooms cannot attach to another organisation's property.
- DELETE archives (`status=archived`); hard delete is not used.

## Audit

Lightweight inserts into `audit_events` on create/update/archive via `app.records.audit_hook`.
Full audit framework remains F1.7.
