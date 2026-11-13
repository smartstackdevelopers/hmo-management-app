# Authentication and Security Guide (F8.9)

Supported patterns: API keys, OAuth2 bearer headers (F6.4 REST connector), webhook HMAC (`integration_hub.webhooks`), organisation JWT + RBAC.

Rotate credentials via F6.4 integration update flows. Webhook signing secrets are stored encrypted at rest.