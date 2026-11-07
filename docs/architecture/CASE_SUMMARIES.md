# F3.5 — Case Summaries Workflow

## Overview

Generates a versioned, AI-labelled case summary from authorised records that already exist for one tenant in the caller's organisation:

- Tenant profile (name, status, tenancy reference, profile needs/goals text)
- Daily logs (excluding voided), limited to the latest 20
- Meetings, appointments, and follow-ups
- Support plans and goals (titles, status, plan objectives — not internal notes)
- Incidents, complaints, and maintenance requests linked to the tenant
- Document **metadata** linked to the tenant (restricted titles are withheld; file bytes are not read)

The workflow does not create a second case record and does not edit support plans, case status, housing decisions, or source notes.

## Workflow

1. An authorised user requests a summary for a `tenant_id` (`POST /api/v1/case-summaries`).
2. Core API checks `ai.case_summary.run` and the F2.1 caseload gate (support workers must have an active assignment).
3. Source identifiers and update timestamps are fingerprinted. The same fingerprint returns the current version unless `force=true`.
4. Core API calls the shared AI service workflow `case_summary` (F3.1), which uses F3.2 routing and F3.3 budget reservation. Feature id: `ai.workflow.case_summaries`. Low-cost routing is the default.
5. When `AI_SERVICE_BASE_URL` is unset outside production, core API uses the same grounded composer locally and labels `generation_method=structured_heuristic`.
6. Output is validated before insert. Invalid output, provider failure, or an exhausted budget returns an error and does not save a summary.
7. Each successful run inserts a new `case_summaries` row (`pending_review`). Previous versions stay.
8. A reviewer with `ai.case_summary.review` approves or rejects. That changes only the summary status and review fields.
9. If source timestamps change, `GET` sets `stale=true`. `POST /{id}/regenerate` writes the next version.

## AI accuracy

- Heuristic text is assembled only from the collected packet.
- Concerns are included only for incidents, complaints, and high/urgent/emergency maintenance, each with `source_id` and `explicitly_recorded=true`.
- A model concern whose `source_id` is not in the packet is rejected (HTTP 422).
- OpenAI responses that are not valid JSON or fail the schema are errors. They are not stored as a successful heuristic.
- The summary states it is AI-generated and is not a diagnosis, safeguarding conclusion, legal finding, or risk classification.
- Cache keys include organisation id (F3.2). Tenant packets are not shared across organisations.

## Permissions

| Permission | Roles |
| --- | --- |
| `ai.case_summary.run` | Support Worker, Organisation Admin, Super Admin |
| `ai.case_summary.read` | Support Worker, Organisation Admin, Super Admin |
| `ai.case_summary.review` | Organisation Admin, Super Admin |

Support workers can generate and read assigned cases. They cannot approve or reject.

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/case-summaries` body `{ tenant_id, force }` |
| GET | `/api/v1/case-summaries/{id}` |
| GET | `/api/v1/case-summaries/tenants/{tenant_id}/versions` |
| GET | `/api/v1/case-summaries/{id}/sources` |
| POST | `/api/v1/case-summaries/{id}/review` body `{ decision: approve\|reject, review_comment }` |
| POST | `/api/v1/case-summaries/{id}/regenerate` |

## Database

Migration `20261107_1600_f35` creates `case_summaries` with organisation RLS (`hmore_org_isolation`). Unique `(organisation_id, tenant_id, version_number)`.

Stored per version: requester, reviewer, timestamps, prompt/provider/model metadata, section JSON, missing information, recorded concerns, source refs, fingerprint, status (`pending_review`, `approved`, `rejected`, `failed`).

## Audit

`ai.case_summary.requested`, `.completed`, `.failed`, `.approved`, `.rejected`, `.regenerated`, `.denied`.

Payloads store identifiers and counts, not full note bodies or prompts.

## Environment

| Variable | Role |
| --- | --- |
| `AI_SERVICE_BASE_URL` | Core API → AI service. Empty in non-production uses the local grounded composer. |
| `AI_SERVICE_TOKEN` | Service-to-service bearer token. Must match the AI service. |
| `AI_SERVICE_TIMEOUT_SECONDS` | Core API client timeout (default 60). |
| `LLM_PROVIDER` | `none` (heuristic), `mock` (heuristic, not billing), `openai` (validated JSON). |
| `AI_BUDGET_ENFORCEMENT_FAIL_OPEN` | Production AI service must be `false` with `CORE_API_BASE_URL` set (F3.3). |
| `AI_DEFAULT_MODEL_KEY` | Low-cost route (F3.2). |

No API keys are stored in this feature.

## Frontend

- Case page link: `/dashboard/caseload/{tenantId}` → Case summary
- List / generate: `/dashboard/case-summaries?tenantId=`
- Review: `/dashboard/case-summaries/{id}`

Controls for generate and review are hidden without the matching permission. The API enforces the same checks.

## Testing

See `docs/development/CASE_SUMMARIES_TESTING.md`.

## Known limitations

- Heuristic runs and `LLM_PROVIDER=none|mock` are not real provider calls and are not billed as actual model spend.
- OpenAI text is schema-checked and concern source ids must exist in the packet. Free-text sections are not independently fact-checked token by token.
- The AI prompt store remains in-memory (F3.1).
- Collectors cap each record type (10–20 rows) and truncate long note text. Older records are omitted from that version and listed only if absent categories produce a missing-information line.
- Document contents, support-plan internal notes, and meeting internal notes are not sent to the model.
- Approval never creates tasks, changes plans, or updates case status.
- Real PostgreSQL, Redis, Celery, and OpenAI were not required for the local unit suite.
