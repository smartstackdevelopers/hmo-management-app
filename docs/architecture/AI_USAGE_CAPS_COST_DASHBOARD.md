# F3.3 — Per-Organisation AI Usage Caps, Cost Tracking and Dashboard

## Scope

Implements organisation AI budgets, usage metering, verified cost calculation,
hard monthly caps with reservation/reconciliation, cost-per-feature reporting,
and AI cost dashboards for Super Admin and Organisation Admin.

Extends F3.1 (shared AI service) and F3.2 (routing, cache, batch). Does **not**
implement F3.4–F3.15 agents or payment/subscription billing.

## Organisation budget configuration

Table: `organisation_ai_budgets`

| Field | Notes |
| --- | --- |
| organisation_id | Org-scoped; RLS enforced |
| monthly_limit | Numeric(12,4), ≥ 0 — configurable, not universal |
| currency | Explicit ISO code (default GBP) |
| period_kind | `calendar_month` (UTC) |
| effective_from / effective_to | Validity window |
| active | Soft history: prior rows deactivated on upsert |
| warning_threshold_pct | Configurable approaching-limit alert |
| default_reservation_amount | Conservative pre-dispatch hold |
| created_by / updated_by | Audit actors |

Only Super Admin may create/update budgets (`ai.budget.manage`). Organisation
Admins may read their org budget (`ai.budget.read`). Historical rows are retained;
usage records are never rewritten when budgets change.

## Usage metering

Table: `ai_usage_records` — one row per unique `request_id`.

Captured from F3.1/F3.2 metadata where available: organisation, user, workflow,
feature, provider, model, prompt id/version, provider request id, batch job id,
input/output/total tokens, cache hit, escalation, status, duration, cost fields.

Statuses: `completed` | `failed` | `rejected_budget` | `cancelled`

Cost statuses: `actual` | `estimated` | `unavailable`

Rules:

- Never fabricate token counts or prices.
- Failed/rejected executions do not contribute actual spend.
- Duplicate `request_id` is idempotent (no double-count).
- Cache hits without a verified cache-billing rule → `cost_status=unavailable`.

## Pricing and cost calculation

Table: `ai_model_pricing` — operator-configured verified prices only.

Cost = `(input_tokens/1000)*input_price_per_1k + (output_tokens/1000)*output_price_per_1k`

Stored as Numeric with six decimal places. Missing pricing → unavailable (never
invented). Pricing version used for a calculation is stored on the usage row.

## Cost-per-feature tracking

Canonical feature IDs live in `app.ai_usage.features` (API) and
`app.budget.features` (AI service). Planned agent IDs are reserved; usage is
only recorded when a workflow attributes to them. Foundation workflows map to
`ai.infra.*`.

Dashboard breakdowns: by feature, provider, model, execution status.

## Hard cap enforcement

Before billable dispatch, the AI service calls:

`POST /api/v1/internal/ai/budget/reserve`

Core API:

1. Locks the active budget row (`SELECT … FOR UPDATE`).
2. Sums actual completed costs + open reservations for the UTC month.
3. Rejects with HTTP **402** + `ai_budget_exceeded` when remaining < reservation.
4. Otherwise inserts an open reservation keyed by `request_id`.

After execution:

`POST /api/v1/internal/ai/budget/reconcile`

Reconciles reservation against calculated actual cost (or releases on failure).

Non-billable workflows (`foundation_ping`) skip reservation. Background/batch
jobs use the same path (`batch_job_id` recorded). No silent model downgrade on
cap; no fabricated AI output.

### Reservation algorithm limitations

- Pre-execution cost is unknown; reservation uses a conservative configured amount.
- Reservations are estimates, never actual charges.
- Orphaned open reservations can be expired via
  `POST /api/v1/internal/ai/budget/expire-orphans`.

## AI Cost Dashboard

| Audience | Endpoint | Permission |
| --- | --- | --- |
| Org Admin | `GET /api/v1/ai/dashboard` | `ai.cost.dashboard.view` |
| Super Admin | `GET /api/v1/ai/platform/dashboard` | `ai.platform.cost.view` |

UI: `/dashboard/ai-costs` (organisation + optional platform scope).

States: loading/empty/error via page states; budget exhausted and approaching
warnings from live status. No placeholder financial figures.

## RBAC

| Role | Budget manage | Budget/usage read | Org dashboard | Platform dashboard |
| --- | --- | --- | --- | --- |
| Super Admin | yes | yes | yes | yes |
| Organisation Admin | no | yes | yes | no |
| Landlord / Tenant / Support Worker / Maintenance | no | no | no | no |

Organisation isolation via membership context + PostgreSQL RLS. Frontend org IDs
are never trusted for authorization.

## Audit events

`ai.budget.upsert`, `ai.pricing.upsert`, `ai.budget.reserved`,
`ai.budget.reconciled`, `ai.budget.cap_rejected`,
`ai.budget.reservation_expired`, `ai.cost.dashboard.view`

Secrets and full AI prompts are not logged.

## Future agents

Agents (F3.4+) must:

1. Execute only through the shared AI service.
2. Pass a documented `feature_id`.
3. Rely on runtime reserve/reconcile (do not bypass the core API).

## Known limitations

- Estimated costs are not implemented as a billing path; missing data → unavailable.
- Email/SMS budget alerts log intent only unless operators wire confirmed delivery.
- `AI_BUDGET_ENFORCEMENT_FAIL_OPEN` defaults true for local AI service tests; set
  `false` in production with `CORE_API_BASE_URL` configured.
