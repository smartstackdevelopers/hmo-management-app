# Voice notes and optional professional rewrite (F4.4)

F4.4 adds device speech-to-text on the staff daily-note screen, plus an optional AI rewrite. Saving the original note does not depend on speech or on the model.

## Speech

The note screen uses `useDeviceSpeechToText` in `room-ready/hooks/useDeviceSpeechToText.ts` and `expo-speech-recognition`. Recognition runs on the device. The mobile app does not send audio to the AI service.

- Start asks for microphone permission, then listens with interim results.
- Partial text is shown as “Hearing: …”. It is not written into the note until it is final.
- Stop commits a leftover partial if the engine has not yet emitted a final result. A later final with the same text is dropped so it is not appended twice.
- Cancel aborts recognition, clears the partial, and does not change the note.
- If the note field is empty, a final transcript fills it. That includes Clear, and a field the staff member deleted before dictating again.
- If the note field already has text, the final transcript is appended after a newline. A manual edit is kept. The helper is `applyFinalTranscript` in `room-ready/lib/hmore/staff/voiceNotes.ts`.
- Permission denied, a missing native module, or an empty capture leaves the typed note usable and shows that message. The screen does not invent a transcript.

Package `expo-speech-recognition` `58.0.1` is installed beside Expo 57. The native module is present only in a development build.

## Optional rewrite

Feature id: `ai.workflow.daily_log_rewrite`.

It is registered in `apps/api/app/ai_usage/features.py`, `WORKFLOW_FEATURE_MAP`, and `apps/api/app/ai_feature_flags/registry.py` with `phase_feature="F4.4"`, `pilot_eligible=True`, and `preserve_enabled_for_existing_orgs=False`.

No new migration. F3.15 already fails closed when a flag row is missing, and `seed_defaults_for_organisation` seeds every registry feature disabled for a new organisation. Existing organisations do not gain this feature until an administrator creates or enables the row. Because it is pilot-eligible, availability needs `enabled` and `pilot_enabled`.

`POST /api/v1/daily-logs/rewrite` requires an organisation context and `require_daily_log_write` (support worker, or super admin). When `tenant_id` is sent, the same caseload assignment check used for daily logs applies. The body is `{ "text": string (1..20000), "tenant_id"?: uuid }`. The handler calls `require_feature_available` for `ai.workflow.daily_log_rewrite`, then the shared AI service workflow `daily_log_rewrite`. A 402 from budget reservation is returned as AI budget exceeded and an activity row is recorded with `rejected_budget`. The response is `{ rewritten_text, activity_id?, request_id?, prompt_version? }`. The handler does not insert a `DailyLog`.

The AI service prompt id is `hmore.daily_log_rewrite.v1`. Input is `{ text, locale? }`. Output is `{ rewritten_text }`. The prompt asks for grammar and clarity only, and tells the model to preserve names, dates, and uncertainty and not to invent medical, safeguarding, or other events. The workflow does not attach source references or a confidence score. Activity logging stores confidence kind `unavailable`. Usage is attributed to `ai.workflow.daily_log_rewrite`. The mobile app has no LLM key. The core API calls the AI service with the existing service token.

There is no silent rewrite when the model is off. `LLM_PROVIDER=none`, a missing AI service URL, or an unreachable service returns an error. The staff member can still save the original note or a device draft.

## Confirmation

Speech, rewrite, accept, reject, and feedback do not submit the note. Accept copies the edited rewrite into the note field. Reject leaves that field unchanged. Save original note opens a confirm dialog and only then calls `POST /daily-logs`. Save draft uses the existing offline draft store and does not claim the note is on the server. If the device is offline or the save fails, the draft remains on the device, as in F4.2.

Report incorrect calls `POST /api/v1/ai-activity/{activity_id}/feedback` with category `incorrect_information` when `activity_id` is present. Feedback still depends on the existing F3.14 activity feature being available for the organisation. A rewrite with no activity id cannot be reported, and the screen says so.

Support workers do not have `ai.feature_flags.read`, so the note screen does not call `GET /ai-feature-flags`. It tries the rewrite and shows the disabled message on 403.
