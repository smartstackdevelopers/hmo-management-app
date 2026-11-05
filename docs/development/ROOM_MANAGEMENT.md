# Room Management (F1.6)

## Endpoints

| Method | Path | Permission |
| --- | --- | --- |
| POST | `/api/v1/rooms` | `rooms.manage` |
| GET | `/api/v1/rooms` | `rooms.read` |
| GET | `/api/v1/rooms/{id}` | `rooms.read` |
| PATCH | `/api/v1/rooms/{id}` | `rooms.manage` |
| DELETE | `/api/v1/rooms/{id}` | `rooms.manage` (archives) |

Filter: `property_id`, `q`, `status`, pagination.

## Rules

1. Room must belong to an in-org property
2. `organisation_id` copied from trusted context / parent property
3. `max_occupancy` positive when set
4. Unique `(property_id, label)`
5. Archived properties reject new rooms
6. No hard delete in F1.6
