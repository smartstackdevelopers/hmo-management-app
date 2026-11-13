# Provider integration guide

**Status:** Mock/test only until client approves telephony subscription.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `VOICE_CALLING_GLOBAL_ENABLED` | Platform kill switch (default `false`) |
| `VOICE_WEBHOOK_SIGNING_SECRET` | HMAC for `X-Voice-Signature` |
| `VOICE_TWILIO_ACCOUNT_SID` / `VOICE_TWILIO_AUTH_TOKEN` | **PENDING APPROVAL** |

## Twilio (prepared, not live)

When credentials absent, organisation `provider_mode` reverts to `pending_approval`.

Do not place real calls from CI or dev without written approval.
