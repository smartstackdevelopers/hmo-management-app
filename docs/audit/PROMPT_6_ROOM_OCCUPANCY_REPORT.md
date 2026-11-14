# PROMPT 6 — Room occupancy (M14)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` |

## Summary

| ID | Feature | Status |
| --- | --- | --- |
| **M14.1** | Settings / survey pack | **PARTIAL** — API `occupancy-surveys`; web `occupancy-survey` is checklist shell pointing to API/docs; `test_f110_occupancy_survey.py` postgres test **skipped** |
| **M14.2** | Manual / demo state | **PARTIAL** — `room-occupancy` + `RoomOccupancyDashboard` loads DB via `roomOccupancyApi`; UI states **“Estimated people counts only”** and blocks live camera until approval gate |
| **M14.3** | Live camera ingest | **DEFER** — gate + copy explicitly disable RTSP/live; plan accepts DEFER for local 100% |

**M14 completion:** **~67%** (2 active rows **PARTIAL**, 1 **DEFER** documented).

## UI honesty (M14.2)

- No fake “live” counts presented as authoritative — `live_counting_active` and approval gate surfaced.
- Amber privacy gate section; outstanding requirements listed from API.

## Tests executed

| File | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: |
| `test_f65_room_occupancy.py` | 5 | 1 | 0 |
| `test_f110_occupancy_survey.py` | 5 | 1 | 0 |

Skipped postgres: isolation / CRUD / cross-org denial.

## Alerts

Room occupancy sweep registered in Celery beat (`hmore.room_occupancy.sweep`) — **PASS** (registration only).

## Gaps

- Postgres integration for approval gate + survey CRUD.
- Rich interactive survey forms on web (currently API + checklist doc).

## Out of scope

Camera ingest, CV, identity tracking — **DEFER** per plan.