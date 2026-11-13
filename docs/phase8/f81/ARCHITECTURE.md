# AI Voice Calling architecture (F8.1)

**Optional add-on** — not core proposal scope. Uses existing FastAPI API, shared AI metering, LangGraph-capable assistant rules (test mode).

## Components

| Layer | Responsibility |
| --- | --- |
| `apps/api/app/voice_calling/` | Sessions, STT/TTS mock, assistant text, handover |
| `apps/api/app/api/v1/voice_calling.py` | REST + webhook (signed when secret set) |
| PostgreSQL | `organisation_voice_calling_settings`, `voice_call_sessions`, `voice_call_turns` |
| `apps/web/.../voice-calling` | Admin dashboard (history/stats) |
| AI usage (`FEATURE_VOICE_CALLING`) | Cost-per-turn metering |

## Provider modes

| Mode | Behaviour |
| --- | --- |
| `test` | Mock call IDs, `text:` prefix STT, no network |
| `twilio` | **BLOCKED** until credentials + approval |
| `pending_approval` | Set when Twilio selected without secrets |

## Master switches

- `VOICE_CALLING_GLOBAL_ENABLED=false` (platform default)
- Per-org `enabled=false` until Organisation Admin enables after client approval

## No recording by default

`recording_enabled` requires `privacy_review_complete=true`.
