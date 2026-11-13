# F8.4 LMS Architecture

## Scope

Optional add-on extending (not replacing) F2.3 `staff_training_records` for external evidence tracking.

## Components

- `organisation_lms_settings` — org gate + certificate validity defaults
- Courses → modules → lessons (file refs via `file_metadata`)
- Assignments by user, role, organisation, category
- Enrollments, lesson completions, quizzes, certificates
- API: `/api/v1/lms`

## Platform gate

`LMS_GLOBAL_ENABLED=false` by default.

## Certificates

PDF via `build_simple_pdf`; verification reference at `GET /lms/certificates/verify?ref=...`.

Not external accreditation unless org verifies separately.
