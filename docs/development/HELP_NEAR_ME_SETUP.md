# Help Near Me setup (F5.2)

## Migrate

```bash
cd apps/api
alembic upgrade head
```

Expected head: `20261110_3500_f52`.

## Environment

```env
GEOCODING_PROVIDER=postcodes_io
GEOCODING_TIMEOUT_SECONDS=8
HELP_NEAR_ME_DEFAULT_RADIUS_KM=5
HELP_NEAR_ME_MAX_RADIUS_KM=25
HELP_NEAR_ME_SEARCH_HOURLY_LIMIT=60
HELP_NEAR_ME_REPORT_HOURLY_LIMIT=10
HELP_NEAR_ME_SEARCH_RETENTION_HOURS=24
```

Optional Nominatim:

```env
GEOCODING_PROVIDER=nominatim
GEOCODING_NOMINATIM_USER_AGENT=HMore/1.0 (ops@your-domain)
```

## Admin workflow

1. Create/publish a community service with a UK postcode in the address.
2. Open the listing and click **Geocode from address postcode**.
3. Verify the listing.
4. Tenant Help Near Me search can then return it by distance.

## Tests

```bash
cd apps/api
pytest tests/test_f52_help_near_me.py tests/test_f51_community_directory.py -q
```

Postgres-backed nearby/report tests need `DATABASE_URL`. Offline unit tests cover postcode normalisation and Haversine math.
