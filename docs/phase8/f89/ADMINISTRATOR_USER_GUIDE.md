# Administrator User Guide (F8.9)

1. Enable `INTEGRATION_HUB_GLOBAL_ENABLED` (platform).
2. PATCH `/integration-hub/settings` with `enabled` and `privacy_review_complete`.
3. Use `/dashboard/integration-hub` or F6.4 integrations UI for connections.
4. Bind Phase modules via `PUT /integration-hub/module-bindings/{module_key}`.

Require explicit approval before financial or government data flows.