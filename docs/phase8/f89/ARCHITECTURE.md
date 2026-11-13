# F8.9 Deep Integration Hub Architecture

Optional add-on extending **F6.4** (`/api/v1/integrations`) with provider directory, API registration, webhook subscriptions, module bindings, usage logging, and health views.

- API: `/api/v1/integration-hub`
- Platform gate: `INTEGRATION_HUB_GLOBAL_ENABLED=false`
- Organisation gate: `organisation_integration_hub_settings.enabled`
- Secrets: Fernet via `app.integrations.crypto` (never exposed to web clients)

Connected status is derived from F6.4 integration `connection_status` after successful connection tests only.