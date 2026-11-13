# Webhook Management Guide (F8.9)

Create subscriptions with `POST /api/v1/integration-hub/webhooks`. Deliveries record idempotency keys from payload SHA-256 hashes.

Inbound test endpoint: `POST /api/v1/integration-hub/webhooks/{id}/inbound` with `X-Hub-Signature` and configured signing secret (sandbox only with user auth).