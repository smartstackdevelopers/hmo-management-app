# F3.15 — Organisation AI Feature Flags & Pilot Enablement Controls

## Feature overview

Centralised, organisation-scoped controls to enable/disable implemented Phase 3 AI capabilities for controlled pilots. Enforcement is **backend-first** (API + background jobs). Frontend hiding alone is insufficient.

**F3.15 is never self-gated** — administrators cannot lock themselves out of the feature-flag UI/API.

## Central feature registry

Stable IDs (see `app/ai_feature_flags/registry.py`):

| Feature ID | Name | Phase | Pilot-eligible |
| --- | --- | --- | --- |
| `ai.agent.notes_analysis` | Notes Analysis Agent | F3.4 | No |
| `ai.workflow.case_summaries` | Case Summaries | F3.5 | No |
| `ai.workflow.document_checker` | Smart Document Checker | F3.6 | No |
| `ai.agent.support_planning` | Support Planning Agent | F3.7 | No |
| `ai.agent.housing_application` | Housing Application Agent | F3.8 | No |
| `ai.agent.compliance` | Compliance Agent | F3.9 | No |
| `ai.agent.tenant_assistant` | Tenant Assistant | F3.10 | **Yes** |
| `ai.agent.duplicate_detection` | Duplicate Detection | F3.11 | No |
| `ai.workflow.operational_search` | NL Operational Search | F3.12 | No |
| `ai.workflow.report_draft` | Report Drafts | F3.13 | No |
| `ai.activity.transparency` | AI Activity Transparency | F3.14 | No |

**Not org-toggled (platform infra F3.1–F3.3):** model routing, cache, batch, budgets, cost dashboard.

Unsupported identifiers are rejected (HTTP 422).

## Organisation configuration model

Tables:

- `organisation_ai_feature_flags` — unique `(organisation_id, feature_id)`
- `organisation_ai_feature_flag_history` — immutable change history

Fields: `enabled`, `pilot_enabled`, `revision`, `change_reason`, `updated_by_user_id`, timestamps.

## Default enablement behaviour

| Situation | Behaviour |
| --- | --- |
| Missing row | **Disabled** (fail closed) |
| New organisation | All controllable features seeded **disabled** |
| Existing orgs (migration) | Previously available features seeded **enabled** to preserve access |
| Tenant Assistant (migration) | Enabled+pilot only for orgs listed in `TENANT_ASSISTANT_PILOT_ORGANISATION_IDS` |
| Flag service / DB error | Treat as **unavailable** (never silently enable) |

## Pilot enablement

For pilot-eligible features (`tenant_assistant`):

- Availability requires `enabled=true` **and** `pilot_enabled=true`.
- Enabling with pilot_eligible=true sets pilot on when enabling.
- Env allowlist remains a **secondary** gate for Tenant Assistant during transition.

Pilot enablement never bypasses RBAC, budgets, human approval, or org isolation.

## Role / permission matrix

| Permission | Super Admin | Org Admin | Others |
| --- | --- | --- | --- |
| `ai.feature_flags.read` | ✓ | ✓ | ✗ |
| `ai.feature_flags.manage` | ✓ | ✓ (own org only) | ✗ |

## Availability service

`evaluate_availability` / `require_feature_available` / `is_feature_available`.

Wired into AI execution paths (notes, case summaries, document checks, support plans, housing, compliance, tenant assistant, duplicates, operational search, report drafts, AI activity) and scheduled jobs (skip with audit when disabled).

## Cache invalidation

In-process cache keyed by `(organisation_id, feature_id)`, TTL **15 seconds**. Updates call `cache_invalidate` immediately. Cache never invents `enabled=true`. Failures fall back to DB / fail closed.

## AI usage-cap interaction

Enabling a feature does **not** grant unlimited usage. F3.3 hard caps, reservations, and cost dashboard remain authoritative. Audit metadata records `bypasses_usage_caps: false` and `bypasses_human_approval: false`.

## API

Prefix `/api/v1/ai-feature-flags`

- `GET /registry`
- `GET /` — org configuration
- `GET /history`
- `GET /{feature_id}`
- `PUT /{feature_id}` — enable/disable/pilot (`expected_revision` for optimistic concurrency)

## Audit events

`ai.feature.enabled|disabled|pilot.enabled|pilot.disabled|config.created|config.updated|config.rejected|execution.blocked|defaults.assigned`

## Migration / deployment

Revision: `20261107_2800_f315`

1. Deploy API with migration.
2. Confirm existing orgs retained access for previously available features.
3. Confirm Tenant Assistant only for allowlisted pilot orgs (or enable via UI).
4. Use `/dashboard/ai-feature-flags` for further pilot control.

## Testing

```bash
cd apps/api
pytest tests/test_f315_ai_feature_flags_unit.py -q
pytest tests/test_f315_ai_feature_flags.py -q -m postgres

cd apps/web
npx playwright test e2e/ai-feature-flags.spec.ts
```

## Known limitations

1. Cache TTL is 15s — worst-case stale enable window after disable if a process missed invalidation (invalidation is same-process immediate).
2. Tenant Assistant still also checks env allowlist until operators rely solely on DB flags.
3. Job queues are not deleted on disable; new scheduled runs skip with an audit reason.
