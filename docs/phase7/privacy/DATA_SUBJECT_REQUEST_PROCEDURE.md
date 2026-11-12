# Data subject request procedure (template)

**Status:** Template — requires adoption by the data controller / DPO. HMore software supports registration and workflow only.

## 1. Intake

1. Verify identity of the requester (out of band — organisation process).
2. Register the request in **Dashboard → Privacy → Data subject requests** (`POST /api/v1/privacy/data-subject-requests`).
3. Assign a responsible staff member and due date.

## 2. Categorisation

| Category | HMore field |
|----------|-------------|
| Access | `access` |
| Rectification | `rectification` |
| Erasure | `erasure` |
| Restrict processing | `restrict_processing` |
| Portability | `portability` |
| Object | `object` |

## 3. Authorised review

- **Erasure** and other high-impact requests must reach status `awaiting_authorised_decision` before completion.
- Software blocks `completed` erasure without `completion_evidence` (see API validation).

## 4. Response and evidence

- Record each step in `response_history` via API updates.
- Store completion evidence text (export references, redaction notes) — not legal advice.

## 5. Retention of request records

Retention of DSR logs is an **organisation decision** — configure in privacy retention policies when confirmed.
