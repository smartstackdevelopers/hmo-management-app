# AI data processing review (F7.2)

**Technical review date:** 2026-11-12  
**Legal DPA / transfer mechanisms:** **PENDING APPROVAL** by data controller

## Six agents (proposal scope)

| Agent | Data minimisation (design) | Human approval | Org isolation |
|-------|---------------------------|----------------|---------------|
| Notes Analysis | Staff-initiated; case notes only as sent | Draft output | API org context |
| Support Planning | Plan records | Draft — staff finalises | Yes |
| Housing Application | Application fields | No auto approve/reject | Yes |
| Compliance | Compliance records | Staff review | Yes |
| Job Matching | Employment prep data | Staff review | Yes |
| Tenant Assistant | Pilot org list; capped | Policy-gated feature flag | Yes |

## Controls evidenced in codebase

- Service bearer token between core API and AI service
- `organisation_id` on workflow calls
- AI activity logging (F3.14)
- Feature flags (F3.15)
- Usage budgets/caps (F3.3)

## Outstanding (not claimed complete)

- Signed DPAs with LLM providers
- International transfer assessments (SCCs / UK IDTA) where applicable
- Formal DPIA entries in privacy register — default **not_started** until authorised approval fields set
