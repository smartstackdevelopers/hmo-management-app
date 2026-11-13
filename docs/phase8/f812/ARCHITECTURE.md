# F8.12 Platform Governance Architecture

Composes existing **audit** (`/audit-events`), **privacy** (`/privacy`), **backups** (`/backups`), **integration hub** (F8.9), and **organisation** APIs.

- API: `/api/v1/platform-governance`
- Gate: `PLATFORM_GOVERNANCE_GLOBAL_ENABLED=false`
- Super Admin: `/platform/*` routes with `get_platform_context`
- Organisation Admin: `/org/*` routes with RLS

No legal compliance guarantee — configurable policies only.
