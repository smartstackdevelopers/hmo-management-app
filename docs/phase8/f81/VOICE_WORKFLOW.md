# Voice assistant workflow

1. Incoming (webhook or test API) creates `voice_call_sessions` (`provider_mode=test`).
2. AI disclosure + consent (`consent_required` default true).
3. STT (mock) → rule-based assistant (`assistant.py`) using approved tenant assistant messages.
4. TTS (mock) response; optional handover on emergency/safeguarding/housing decisions.
5. Turns metered via `ai.addon.voice_calling`.
6. End call → duration stored; no audio blobs stored.

Human handover sets `handover_status=pending` for staff queue (dashboard).
