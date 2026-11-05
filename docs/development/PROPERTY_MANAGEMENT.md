# Property Management (F1.6)

## Endpoints

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/api/v1/properties` | `properties.manage` |
| GET | `/api/v1/properties` | `properties.read` |
| GET | `/api/v1/properties/{id}` | `properties.read` |
| PATCH | `/api/v1/properties/{id}` | `properties.manage` |
| DELETE | `/api/v1/properties/{id}` | `properties.manage` (archives) |

## Ownership

- Organisation Admin: all org properties
- Landlord: create stamps `landlord_user_id` to self; list/get limited to own or unassigned
- Maintenance: `properties.read` only (no manage)

## Lifecycle

Archive via DELETE. Active rooms may remain; new rooms cannot be added to archived properties.
