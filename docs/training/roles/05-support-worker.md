# Support Worker — training guide

**Who:** `support_worker`.  
**Web home:** `/dashboard/support-worker`  
**Mobile:** Staff shell in HMore app.

## Caseload

1. Web: **Caseload** / assignments; mobile: **Caseload** tab.
2. Open tenant case — view permitted timeline only.
3. **Never** browse unassigned tenants.

## Daily notes & voice

- **Daily logs** (web) and **Notes** tab (mobile).
- **Voice dictation:** microphone permission — review text before save; AI rewrite optional with approval.

## Visits, tasks, follow-ups

- Mobile: **Visits**, **Tasks**; web: **Tasks**, **Visits**, **Rota** as enabled.
- Complete follow-ups before closing incidents.

## Support plans

- Web: **Support plans** — progress updates per org policy.
- AI **support plan drafts** require human approval before apply.

## Incidents & safeguarding

- **Incidents**, **Safeguarding** — escalate per local policy; HMore records the report.

## Employment support

- Phase 5 modules when enabled for org.

## Room occupancy

- **Staff → Occupancy:** live view only if `occupancy.read`; else surveys/feasibility only (camera live ingest gated by DPIA — F6.5).

## Mobile offline

- Drafts saved encrypted — sync when online; check **Offline drafts** if sync fails.
- Revoked device blocks sync (`device_session_revoked`).

## Push

- Register for push after login; generic notification text only.

## FAQs

**Q: Can AI approve a support plan?**  
A: No — human approval required.

## Screenshots

`docs/training/assets/screenshots/support-worker/` — caseload, notes, occupancy.
