# Connector Development Guide (F8.9)

Implement connectors under `app.integrations.connectors` (F6.4). F8.9 adds directory metadata and module bindings only — no duplicate connector base classes.

New connectors must implement connection testing, scoped credentials, and sync job integration via `IntegrationSyncJob`.