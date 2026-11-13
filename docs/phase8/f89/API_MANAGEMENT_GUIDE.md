# API Management Guide (F8.9)

Register internal or partner APIs with `POST /api/v1/integration-hub/apis`. Use `integration_registered_apis` for slug, version, auth method, and per-minute rate limits.

Request logging flows to `integration_api_usage_log` via `integration_hub.service.log_api_usage` (callable from middleware in future hardening).

Do not expose unpublished FastAPI routes without organisation approval and privacy review.