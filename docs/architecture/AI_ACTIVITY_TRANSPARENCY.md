# F3.14 — AI Activity Logs, Confidence, Sources & Wrong-Answer Feedback

## Feature overview

HMore records authorised AI operations in organisation-scoped **AI activity logs**, exposes **genuine** source references and confidence signals when workflows provide them, and accepts **wrong-answer feedback** for human review only.

Feedback never auto-trains models, rewrites prompts, or changes operational records.

## AI activity data model

| Table | Purpose |
| --- | --- |
| `ai_activity_logs` | Traceable AI operations (links to `ai_usage_records` when metered) |
| `ai_wrong_answer_feedback` | Controlled-category feedback against an activity |
| `ai_feedback_review_events` | Immutable review history |

Activity records store metadata sufficient to investigate what happened **without** copying sensitive prompts, tenant record bodies, or full AI outputs. Output is referenced by `{type, id}` only.

### Indexes

- Organisation + created_at / feature / status / user / visibility

### Migration

- `20261107_2700_f314` (revises F3.13)

## Activity lifecycle

1. AI service (or local workflow) completes.
2. F3.3 `record_and_reconcile` creates an `AiUsageRecord` and a stub `AiActivityLog` (best-effort).
3. Workflows that already hold source refs call `attach_transparency` / `record_local_activity` to preserve them.
4. Authorised users list/filter activities and open details.
5. Users submit feedback; reviewers mark under review / resolve / reject.

## Source-reference handling

- Only refs supplied by the original workflow are shown.
- Sanitiser strips prompts, reasoning, embeddings, tokens, and raw bodies.
- If none exist: **"No available source references for this AI result."**
- Display respects organisation isolation and visibility (`staff` vs `initiator`).

### Workflow coverage

| Workflow | Sources today | Confidence |
| --- | --- | --- |
| Notes Analysis | Yes (daily log ref) | Unavailable |
| Case Summaries | Yes (packet sources) | Unavailable |
| Tenant Assistant | Yes (approved content) | Retrieval coverage when sources used |
| Document Checker | Via usage + optional enrichment | Unavailable unless deterministic rules expose validation |
| Support Planning | Via usage + optional enrichment | Unavailable |
| Housing Application | Via usage + optional enrichment | Deterministic checklist possible later — not fabricated |
| Compliance | Via usage | Unavailable |
| Operational Search | Via usage | Unavailable |
| Report Drafts | Metrics snapshot (not AI sources) | Unavailable |

## Confidence semantics and limitations

- **Never invent percentages.**
- Default: `confidence_kind=unavailable` → display **Confidence unavailable**.
- Allowed kinds: `unavailable`, `retrieval_coverage`, `deterministic_validation`, `human_reviewed`, `model_reported`.
- `model_reported` is explicitly **not calibrated**.
- API always returns `calibrated: false` and `percentage: null`.

## Feedback categories

Controlled values:

- `incorrect_information`
- `incomplete_answer`
- `misleading_answer`
- `unsupported_claim`
- `missing_source`
- `outdated_information`
- `other`

Optional explanation (max 2000 chars). Treated as untrusted text. Rate-limited per user/hour.

## Feedback review workflow

Authorised reviewers (`ai.activity.feedback.review`):

- List / filter feedback
- Open referenced activity
- `start_review` / `assign` / `resolve` / `reject`
- Resolution notes and rejection reasons
- Review history preserved

No automatic prompt/model/business-rule changes.

## Permission matrix

| Permission | Super Admin | Org Admin | Landlord | Tenant | Support Worker | Maintenance |
| --- | --- | --- | --- | --- | --- | --- |
| `ai.activity.read` | ✓ | ✓ | — | ✓ (own initiator only) | ✓ | — |
| `ai.activity.feedback.submit` | ✓ | ✓ | — | ✓ | ✓ | — |
| `ai.activity.feedback.review` | ✓ | ✓ | — | — | — | — |

Tenants never see staff AI activity logs. Initiator-scoped activities (Tenant Assistant) are visible to the initiating user and feedback reviewers.

## Organisation isolation

- RLS on all F3.14 tables
- Service checks `organisation_id` + visibility + RBAC
- Cross-org activity IDs return 404
- Source refs never grant document download rights by themselves

## API

Prefix: `/api/v1/ai-activity`

- `GET /` — paginated activity history
- `GET /categories` — feedback categories + confidence note
- `GET /{id}` — activity detail (audits source access when sources exist)
- `POST /{id}/feedback` — submit feedback
- `GET /feedback` — reviewer list
- `GET /feedback/stats` — category/status aggregates
- `GET /feedback/{id}` — detail + history
- `POST /feedback/{id}/review` — review actions

## Retention and privacy

Follows existing HMore audit and AI usage retention. Activity logs intentionally omit sensitive payloads. Do not retain unrestricted prompt/output copies for logging. If platform retention rules change, update this feature accordingly — do not invent a conflicting policy here.

## Testing

```bash
cd apps/api
pytest tests/test_f314_ai_activity_unit.py -q
pytest tests/test_f314_ai_activity.py -q -m postgres

cd apps/web
npx playwright test e2e/ai-activity.spec.ts
```

## Known limitations

1. Calibrated confidence is **not** available for most agents; UI shows Confidence unavailable.
2. Not every Phase 3 agent enriches sources beyond usage metadata yet; notes analysis, case summaries, and tenant assistant do.
3. Feedback is a human signal only — no self-learning loop.
4. Activity creation from metering is best-effort so AI operations are not blocked if logging fails; usage metering remains the financial source of truth.
