# Administrator guide

**Web:** `/dashboard/voice-calling` (requires `voice_calling.read`).

**API:**

- `GET/PATCH /api/v1/voice-calling/settings`
- `GET /api/v1/voice-calling/dashboard`
- `GET /api/v1/voice-calling/calls`

Enable platform flag + organisation `enabled` after client purchases add-on.

Test incoming call (tenant permission): `POST /api/v1/voice-calling/calls/incoming/test`
