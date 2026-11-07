# F3.4 — Notes Analysis Agent

## Overview

Analyses authorised F2.1 daily notes to produce:

- An **AI-generated** summary (never a verified staff statement)
- Missing-detail suggestions for human review
- Suggested next actions (not auto-executed)

Uses the shared AI service (F3.1), low-cost routing/caching (F3.2), and organisation AI budgets (F3.3).

## Workflow

1. Authorised user (Support Worker on caseload, or Org Admin) requests analysis for a `daily_log_id`.
2. Core API validates caseload/org access and fingerprints the note (`source_note_version`).
3. Existing analysis for the same version is returned idempotently (unless `force=true`).
4. Core API calls AI service `notes_analysis` workflow (or local heuristic when AI service URL is unset in non-production).
5. Structured output is validated and stored with suggestion rows (`pending`).
6. Human reviewers approve/reject/dismiss suggestions and mark the analysis reviewed.
7. **No automatic mutation** of the source daily note.

## Overnight batch

- Configurable cron hint: `NOTES_ANALYSIS_BATCH_CRON` (default `0 2 * * *`).
- API: `GET /api/v1/notes-analysis/batch/eligible`, `POST /api/v1/notes-analysis/batch/run`.
- Skips voided notes and note versions already analysed.
- Respects the same permissions and budget path as on-demand runs.

## Prompt

- ID: `hmore.notes_analysis.v1`
- Version: `1.0.0`
- Feature metering ID: `ai.agent.notes_analysis`

## Permissions

| Permission | Roles |
| --- | --- |
| `ai.notes.analysis.run` | Support Worker, Org Admin, Super Admin |
| `ai.notes.analysis.read` | Support Worker, Org Admin, Super Admin |
| `ai.notes.analysis.review` | Org Admin, Super Admin |
| `ai.notes.analysis.inbox.read` | Support Worker, Org Admin, Super Admin |

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/notes-analysis/analyse` |
| GET | `/api/v1/notes-analysis/analyses/{id}` |
| GET | `/api/v1/notes-analysis/inbox` |
| POST | `/api/v1/notes-analysis/suggestions/{id}/decide` |
| POST | `/api/v1/notes-analysis/analyses/{id}/review` |
| GET/POST | `/api/v1/notes-analysis/batch/eligible`, `/batch/run` |

## Frontend

- Inbox: `/dashboard/notes-analysis`
- Detail/review: `/dashboard/notes-analysis/[id]`

## Known limitations

- Heuristic fallback is used when no LLM is configured; it only uses explicit note fields.
- Approving a suggestion does **not** auto-create tasks/visits (human uses existing modules).
- AI service prompt store remains in-memory (F3.1 limitation).
- Full AI activity feedback UI is F3.14.
