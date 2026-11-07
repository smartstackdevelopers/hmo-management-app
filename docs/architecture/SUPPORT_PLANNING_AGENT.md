# F3.7 — Support Planning Agent

## Overview

Authorised staff can prepare a support-plan draft from records they are already allowed to see. The draft is assistance for review. It is not an approved support plan.

Generating, editing, submitting, approving, or rejecting a draft does not change the support plan. Approved suggestions are added only when someone with support-plan manage permission calls apply.

## Workflow

1. Collect the same authorised case packet used for case summaries, plus the latest approved case summary when one exists.
2. Build suggestions from recorded needs. Missing needs, goals, notes, or plans are listed as gaps.
3. Save a new draft version. The same source fingerprint returns the open draft unless regeneration is requested.
4. A person edits the draft, then submits it.
5. A reviewer with `ai.support_plan_draft.review` approves or rejects it.
6. Apply calls the existing goal and milestone services. It does not change plan status, assign staff, or set dates.

If source records change after generation, apply stops and asks for a new draft.

## AI

Feature id: `ai.agent.support_planning`. Workflow: `support_plan_draft`.

The shared AI service is used when `AI_SERVICE_BASE_URL` is set. Output must match the draft schema and cite source ids from the packet. Decision language is rejected. A usage-cap response (HTTP 402) does not save a draft. Outside production, with no AI URL, the API uses a local restatement of recorded needs.

## API

| Method | Path |
| --- | --- |
| POST | `/api/v1/support-plan-drafts` |
| GET | `/api/v1/support-plan-drafts/tenants/{tenant_id}` |
| GET | `/api/v1/support-plan-drafts/{id}` |
| PATCH | `/api/v1/support-plan-drafts/{id}` |
| POST | `/api/v1/support-plan-drafts/{id}/submit` |
| POST | `/api/v1/support-plan-drafts/{id}/approve` |
| POST | `/api/v1/support-plan-drafts/{id}/reject` |
| POST | `/api/v1/support-plan-drafts/{id}/apply` |

## Permissions

| Permission | Roles |
| --- | --- |
| `ai.support_plan_draft.run` | Support Worker, Organisation Admin, Super Admin |
| `ai.support_plan_draft.read` | Support Worker, Organisation Admin, Super Admin |
| `ai.support_plan_draft.review` | Organisation Admin, Super Admin |

Apply also requires permission to manage the support plan and the existing caseload check. Support workers can apply an approved draft on an assigned case. They cannot approve one.

## Database

Migration `20261107_2000_f37` adds `support_plan_drafts` with organisation row-level security. Previous draft versions stay in the table.

## Known limitations

- Suggestions restate recorded needs. They do not invent deadlines, progress, strengths, or staff assignments.
- Apply adds goals and milestones to an existing editable plan. It does not create a plan or revise and close the current one.
- Draft generation runs in the API request.
- Approved case-summary text is referenced, not treated as a new operational fact.
