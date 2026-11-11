# Employment preparation architecture (F5.3)

Skills Assessment, CV Builder, Job Application Tracker, interview prep and a basic career roadmap for HMore tenants.

## Scope

- Tenant-owned skills assessment (JSONB sections; incomplete drafts allowed).
- Multiple CV versions with five professional templates and private PDF export.
- Optional AI CV wording assist via existing AI gateway (`ai.workflow.cv_wording`); human approval required; never invents facts.
- Job applications with status history events, interview notes and follow-ups.
- Career goals / roadmap suggestions (not enrolment, not F5.4 matching).
- Staff web summary only: assessment status, skill names, CV/application counts — not full CV or private application notes.

## Data

| Table | Purpose |
| --- | --- |
| `tenant_skill_assessments` | One assessment per tenant |
| `tenant_cvs` | CV versions + template + `pdf_file_id` |
| `tenant_job_applications` | Application tracker |
| `tenant_job_application_events` | Status change history |
| `tenant_career_goals` | Roadmap goals |
| `tenant_interview_notes` | Interview prep notes |

All tables are organisation-scoped with RLS. CV PDFs use private `file_metadata` storage (no public URLs).

## Permissions

- `employment.prep.manage.own` — tenant self-service
- `employment.prep.read.assigned` — support worker assigned-tenant summary
- Existing `employment_support.manage.assigned` / `tenants.manage` for broader staff access

## API

Prefix: `/api/v1/employment`

Assessment, CVs (CRUD, duplicate, PDF generate/download, assist), applications (+ dashboard), roadmap, career goals, interview prep, staff summary.
