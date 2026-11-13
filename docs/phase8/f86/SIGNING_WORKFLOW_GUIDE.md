# Signing Workflow Guide

1. Create request with signers and workflow type.
2. `POST .../send` moves to `pending` and notifies signers.
3. Each signer uses `POST /signers/{id}/sign` with consent.
4. Sequential workflows enforce signing order.
5. Completion updates status when all signers finish.

Rejections cancel the request for manual follow-up.
