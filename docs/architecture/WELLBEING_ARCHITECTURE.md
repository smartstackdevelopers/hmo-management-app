# Wellbeing architecture (F5.5)

Non-clinical tenant wellbeing tools: daily check-ins, routines, exercise/mindfulness libraries, local directory and support navigator.

## Privacy

- Check-ins, notes and routines are tenant-owned (`wellbeing.manage.own`).
- Staff and landlords do **not** receive mood/check-in access by default.
- Staff may manage resource/directory listings (`wellbeing.resources.manage`) only.

## Non-clinical rules

Disclaimer states HMore is not a medical service; check-ins are not diagnoses; crisis guidance points to 999 / Samaritans 116 123. No automated clinical risk classification.

## Integrations

- Local directory merges org wellbeing entries with published F5.1 `local_service` community listings.
- Optional routine reminders use existing F4.3 push delivery (`wellbeing_routine_reminder`).
- Default exercise/mindfulness resources seed per organisation on first tenant list (general guidance only).
