# Voice notes setup (F4.4)

Speech and the optional rewrite are in the Expo app `room-ready/`. From the monorepo root:

```bash
npm install
npm run typecheck -w room-ready
npm test -w room-ready
```

API and AI service checks for this feature:

```bash
cd apps/api
pytest tests/test_f44_daily_log_rewrite_unit.py tests/test_f315_ai_feature_flags_unit.py -q

cd apps/ai-service
pytest tests/test_daily_log_rewrite.py -q
```

## Device speech

`expo-speech-recognition` needs a development build. Expo Go does not load the native module. From `room-ready/`:

```bash
npx expo start --dev-client
```

Create the dev client with EAS or `npx expo run:android` / `npx expo run:ios` when a device or emulator is available. Grant microphone permission when the note screen asks. If permission is denied, or the recogniser is missing, the note field still accepts typing and the screen says speech recognition is not available. Dictation language is `en-GB`.

This setup does not include a physical-device speech check.

## AI rewrite flag

The feature id is `ai.workflow.daily_log_rewrite`. It is off until an organisation administrator turns it on.

- A new organisation is seeded with the flag disabled.
- An existing organisation has no row until someone configures it. A missing row is disabled.
- The feature is pilot-eligible. `POST /api/v1/daily-logs/rewrite` succeeds only when `enabled` is true and `pilot_enabled` is true.

An organisation admin (or super admin) with `ai.feature_flags.manage` can enable it:

```http
PUT /api/v1/ai-feature-flags/ai.workflow.daily_log_rewrite
Content-Type: application/json

{
  "enabled": true,
  "pilot_enabled": true,
  "change_reason": "Pilot F4.4 voice-note rewrite"
}
```

If the organisation already has a disabled row, send both `enabled` and `pilot_enabled`. Sending only `enabled: true` on an existing row leaves `pilot_enabled` as it was, and a pilot-eligible feature stays unavailable.

Support workers cannot read the flag list. The note screen learns that the feature is off from the rewrite response (403) and still allows Save original note and Save draft.

## Model and caps

The mobile app does not contain an LLM key. Run the AI service and point the API at it with `AI_SERVICE_BASE_URL` and `AI_SERVICE_TOKEN`, as in `docs/development/AI_SERVICE_LOCAL.md`. Set `LLM_PROVIDER=openai` on the AI service for a real rewrite. `LLM_PROVIDER=none` makes rewrite return unavailable. The shared mock provider echoes text and does not return rewrite JSON, so a call with `LLM_PROVIDER=mock` fails instead of inventing a rewritten note. Unit tests stub the completion. None of those failures save the note or report success.

Budget caps are unchanged. When the organisation has no active budget, or the hard cap is reached, reserve returns 402 and the note screen says the usage limit has been reached. The original note can still be saved. Enabling the feature does not raise the cap. See `docs/development/AI_USAGE_CAPS_TESTING.md`.

Wrong-answer feedback uses the existing activity endpoint and still requires `ai.activity.transparency` to be available for that organisation.

## What not to expect

- Speech or rewrite does not auto-save a daily log.
- Save original note asks for confirmation first.
- The rewrite does not add sources or a confidence percentage. Activity confidence is “unavailable”.
- Offline draft sync from F4.2 is unchanged: a draft stays on the device until a daily-log save receives HTTP 2xx.
