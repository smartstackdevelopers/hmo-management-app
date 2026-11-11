# Help Near Me (F5.2)

Tenants find published community support services near a UK postcode and can report incorrect directory information.

F5.2 reuses F5.1 `community_services` rows. It does not duplicate catalogue records or seed fake coordinates.

## Geocoding

- Default provider: **postcodes.io** (`GEOCODING_PROVIDER=postcodes_io`) — no API key.
- Optional: Nominatim (`GEOCODING_PROVIDER=nominatim`) with a descriptive User-Agent.
- Pattern matching alone never proves a postcode is valid; the provider response does.
- Service coordinates are set by admin geocode-from-address or explicit manual coordinates.

## Nearby search

- `GET /api/v1/help-near-me/nearby`
- Bounding-box prefilter + Haversine distance (km / miles)
- Configurable radius (`HELP_NEAR_ME_DEFAULT_RADIUS_KM`, max `HELP_NEAR_ME_MAX_RADIUS_KM`)
- Excludes inactive listings and services without real coordinates
- Rate-limited via short-lived `help_near_me_search_events` (retention hours configurable)

PostGIS was not introduced; latitude/longitude floats keep the schema aligned with the existing stack.

## Reports and moderation

- Tenant reports create `community_service_outdated_reports` review requests
- Reports never auto-verify or delete listings
- Verified listings move to `needs_review` when reported
- Admin moderation statuses: submitted → under_review → information_confirmed / listing_updated / reverified / rejected / closed

## Clients

- Tenant Mobile App: Help Near Me list/map alternative + report form
- Web dashboard: `/dashboard/help-near-me` plus geocode action on community directory detail
