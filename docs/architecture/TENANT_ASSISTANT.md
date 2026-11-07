# F3.10 — Tenant Assistant Pilot

## Overview

Pilot conversational assistant for authenticated tenants. Answers are grounded only in **approved and cached organisation content**. The assistant does not make official operational decisions.

## Approved content sources

Existing HMore approval/publish mechanisms (no invented policy):

1. **F2.12 announcements** — `status=published`, audience `tenants_only` / `organisation_all` / eligible `custom_users`, not expired. Draft, cancelled, expired, and `staff_only` / `landlords_only` are excluded.
2. **F2.8 emergency content** — `maintenance_emergency_content` rows with `approved_for_use=True` only.

Private case notes, staff communications, and unapproved documents are never indexed.

## Pilot restriction

Not globally enabled. Configure:

```text
TENANT_ASSISTANT_PILOT_ORGANISATION_IDS=<uuid>[,<uuid>...]
TENANT_ASSISTANT_HOURLY_LIMIT=30
```

Empty allowlist = disabled for all organisations. This uses existing Settings/env configuration (not F3.15 feature-flag UI).

## Workflow

1. Tenant asks a question (role + `ai.tenant_assistant.ask` + pilot org).
2. Load approved content for the organisation; cache by org + content fingerprint.
3. Score/select relevant snippets (keyword overlap). No unrestricted DB vector search.
4. Escalate unsafe topics (housing decisions, other tenants, emergencies, record changes) to human-support guidance.
5. If snippets exist, call shared AI `tenant_assistant` workflow with snippets only.
6. Validate answer; return source references.

## API

| Method | Path |
| --- | --- |
| GET | `/api/v1/tenant-assistant/availability` |
| POST | `/api/v1/tenant-assistant/ask` |
| GET | `/api/v1/tenant-assistant/conversations` |
| GET | `/api/v1/tenant-assistant/conversations/{id}` |

## Permissions

| Permission | Role |
| --- | --- |
| `ai.tenant_assistant.ask` | Tenant |
| `ai.tenant_assistant.read` | Tenant |

Conversations are isolated by `organisation_id` + `user_id`.

## Database

Migration `20261107_2400_f310`: conversations, messages, rate windows + RLS.

## Known limitations

- Pilot requires manual env configuration per organisation.
- Retrieval is keyword-based over approved content only.
- Feedback/wrong-answer UI is out of scope (F3.14).
- Does not create complaints, change records, or decide housing eligibility.
