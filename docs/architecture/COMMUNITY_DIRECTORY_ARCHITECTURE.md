# Community directory (F5.1)

HMore tenants need a reliable, organisation-scoped directory of community support services:

- Food banks
- Community kitchens
- Clothing banks

F5.1 extends the F4.1 `community_services` catalogue. It does not create a second backend or seed fake listings.

## Data model

`community_services` (extended):

- Service content: name, category, description, address, opening days/hours, eligibility, referral requirements, contact, instructions
- Clothing banks may set `clothing_service_type` (`provides_clothing`, `accepts_donations`, `both`)
- Verification: `verification_status`, `verified_at`, `verified_by_user_id`, `information_source`, internal `verification_notes`
- Actor tracking: `created_by_user_id`, `updated_by_user_id`

`community_service_verification_events`:

- Immutable history of create / verify / content update / flag outdated / deactivate

Verification statuses:

1. `pending_verification` (default for new listings — never auto-verified)
2. `verified`
3. `needs_review` (set after content edits to a verified listing)
4. `outdated`
5. `inactive` (also unpublishes the listing)

## API surface

Tenant / discover (`services.discover`):

- `GET /api/v1/community-services/categories`
- `GET /api/v1/community-services` (published, non-inactive; search, category, pagination, optional field filters)
- `GET /api/v1/community-services/{id}`

Admin (organisation admin / super admin / catalogue writers):

- `GET /api/v1/community-services/admin`
- `GET /api/v1/community-services/{id}/admin`
- `POST /api/v1/community-services`
- `PATCH /api/v1/community-services/{id}`
- `POST /api/v1/community-services/{id}/verify`
- `POST /api/v1/community-services/{id}/flag-outdated`
- `POST /api/v1/community-services/{id}/deactivate`
- `GET /api/v1/community-services/{id}/verification-history`

Tenant responses never include `verification_notes`.

## Clients

- Tenant Mobile App: Community directory list + detail (`room-ready` community screens)
- Web dashboard: `/dashboard/community-directory` for authorised admins

## Out of scope

- F5.2 Help Near Me / postcode nearby search
- F5.3–F5.6
