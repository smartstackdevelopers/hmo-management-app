# Occupancy Feasibility Pack (F1.10)

Client-facing pack for HMore Phase 1. Complements the [site-survey checklist](./OCCUPANCY_SITE_SURVEY_CHECKLIST.md).

## 1. Why this pack exists

The approved proposal requires a **site survey for camera/occupancy feasibility** before any occupancy module build. Phase 1 delivers the survey foundation only. Live occupancy counting, sensors, and the ten mandatory occupancy features are deferred to later phases after DPIA, signage, and retention gates.

## 2. Who uses it

| Role | Typical use |
| --- | --- |
| Organisation Admin | Owns survey completion and feasibility decision for the organisation |
| Landlord | Contributes property access and condition knowledge (`inspections.manage`) |
| Super Admin | May review surveys across orgs under platform process |
| Support Worker | May read occupancy-related materials where `occupancy.read` applies; not the survey author by default |
| Tenant / Contractor | Out of scope for survey authorship |

## 3. How to run a survey in HMore

1. Ensure the property (and rooms, if known) exist via F1.6 APIs.
2. Create a survey: `POST /api/v1/occupancy-surveys` with `property_id`.
3. Update section payloads (building, facilities, health/safety, accessibility, camera_feasibility_notes).
4. Add per-room assessments: `POST /api/v1/occupancy-surveys/{id}/room-assessments`.
5. Record findings/actions: `POST /api/v1/occupancy-surveys/{id}/findings`.
6. Optionally attach private evidence via F1.8 file id on findings.
7. Complete with a `feasibility_status` and summary (`PATCH` status `completed`).

API responses include an explicit disclaimer that feasibility is **not** a legal certification.

## 4. Feasibility statuses

| Status | Meaning |
| --- | --- |
| `suitable` | Operationally suitable based on recorded findings |
| `suitable_with_actions` | Suitable after listed remedial actions |
| `not_suitable` | Not suitable for intended use at this time |
| `further_assessment_required` | Critical information or specialist review still needed |

## 5. Camera / DPIA gate (mandatory before any later occupancy build)

Confirm and document (separately from camera software):

1. Room types and which spaces are communal-only.
2. Purpose of any future counting.
3. Existing cameras (inventory only).
4. Who may view counts (Org Admin + permitted Support Workers per proposal).
5. Retention rules.
6. Accuracy needs.
7. DPIA, signage, and retention approval.

**Do not** install or integrate cameras under F1.10.

## 6. Finding / action tracking

Each finding supports category, severity, description, recommended action, optional room link, optional evidence file, status, and notes. Do not invent owners or deadlines; leave blank when unknown.

## 7. Related repository artefacts

| Artefact | Location |
| --- | --- |
| Checklist | `docs/operations/OCCUPANCY_SITE_SURVEY_CHECKLIST.md` |
| Architecture | `docs/architecture/OCCUPANCY_SURVEY_ARCHITECTURE.md` |
| API | `/api/v1/occupancy-surveys` |
| Dashboard shell entry | `/dashboard/occupancy-survey` |

## 8. Future dependencies (documented, not built)

- F6.5 full occupancy module after DPIA Go.
- DPIA / signage / retention workflow productisation.
- Edge counting hardware evaluation.
- Malware scanning on evidence files (F1.8 limitation).
