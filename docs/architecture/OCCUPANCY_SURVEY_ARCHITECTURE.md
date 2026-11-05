# F1.10 Occupancy Survey Architecture

## Intent

Capture site-survey and feasibility data for HMore occupancy **before** any camera or counting software. No CV, streaming, or detection code ships in this feature.

## Data model

| Table | Purpose |
| --- | --- |
| `occupancy_site_surveys` | Survey header + section JSON + feasibility outcome |
| `occupancy_survey_room_assessments` | Per-room observations (optional `room_id`) |
| `occupancy_survey_findings` | Risks/actions; optional `evidence_file_id` → `file_metadata` |

All tables are organisation-scoped with FORCE RLS matching F1.5 patterns.

## Permissions (reused)

| Action | Permissions accepted |
| --- | --- |
| Read | `occupancy.read` **or** `occupancy.alerts.manage` **or** `inspections.manage` |
| Write | `occupancy.alerts.manage` **or** `inspections.manage` |

Super Admin receives occupancy read/manage for platform oversight. No new permission identifiers were added.

## Audit events

`occupancy_survey.create|update|complete`, `occupancy_survey.room_assess`, `occupancy_survey.finding.create|update`.

## Explicit non-implementation

Cameras, sensors, live counts, facial recognition, occupancy alerts automation, and retention engines are **out of scope**.
