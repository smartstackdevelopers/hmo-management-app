# F3.8 — Housing Application Agent

## Overview

Analyses an existing housing application using the organisation evidence checklist and recorded application fields. The result is a checklist status and a gap narrative for staff.

This analysis does not determine housing eligibility, allocation, approval, or rejection. Final decisions stay in the existing human housing workflows.

## Workflow

1. Load the authorised housing application.
2. Evaluate recorded application fields.
3. Evaluate existing evidence checklist items and associated file metadata.
4. Optionally note existing Smart Document Checker extraction statuses for associated files.
5. Ask the shared AI service for a gap narrative only when gaps need explanation.
6. Allow staff to confirm or dismiss findings. Review does not change the application, waiting list, or decisions.

## Requirement sources

Checklist requirements come from organisation evidence checklist templates and items already configured in HMore. The agent does not invent legal, council, or eligibility requirements. If no checklist items exist, it reports that verification could not be performed.

## AI

Feature id: `ai.agent.housing_application`. Workflow: `housing_application_analysis`.

The model receives finding codes and titles, not a housing decision. Narratives that approve, reject, allocate, or decide eligibility are rejected. HTTP 402 keeps the rule-based checklist results and sets `ai_status=skipped_budget`.

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/housing-application-analyses` |
| GET | `/api/v1/housing-application-analyses/applications/{application_id}` |
| GET | `/api/v1/housing-application-analyses/{id}` |
| POST | `/api/v1/housing-application-analyses/{id}/review` |
| POST | `/api/v1/housing-application-analyses/findings/{id}/decide` |

## Permissions

| Permission | Roles |
| --- | --- |
| `ai.housing_application.run` | Support Worker, Organisation Admin, Super Admin |
| `ai.housing_application.read` | Support Worker, Organisation Admin, Super Admin |
| `ai.housing_application.review` | Organisation Admin, Super Admin |

Application visibility reuses the existing housing application access rules.

## Database

Migration `20261107_2200_f38` adds `housing_application_analyses` and `housing_application_analysis_findings` with organisation row-level security.

## Known limitations

- Document content is not re-extracted here. Existing document-check statuses are referenced when available; otherwise the analysis states that only metadata was considered.
- The agent does not create checklist items, approve applications, change waiting-list positions, or allocate properties.
- Analysis runs in the API request.
