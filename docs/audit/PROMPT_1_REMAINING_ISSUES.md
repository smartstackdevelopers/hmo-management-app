# PROMPT 1 — Remaining issues

## Manual verification still required

1. **Super Admin organisations (M10.1)** — Sign in as Super Admin with Auth0, API on `:8000`, `PLATFORM_GOVERNANCE_GLOBAL_ENABLED=true`, open `/dashboard/super-admin/organisations`. Confirm table loads and create refreshes list.
2. **Mobile HMore path** — `room-ready/.env` with `EXPO_PUBLIC_HMORE_API_URL=http://localhost:8000/api/v1` and Auth0 vars; confirm tenant flows use `hmore/client`, not legacy `lib/api`.
3. **Legacy demo path** — Only if you need password Room Ready API: set explicit `EXPO_PUBLIC_API_URL` (no default).

## Known limitations (not regressions from this sprint)

| Item | Status |
|------|--------|
| Platform org list requires governance add-on flag | By design (`assert_platform_addon`) |
| Organisation list API has no pagination | Full list only (matches backend) |
| `hmore_app` role may persist after downgrade-to-base | Intentional F1.5 downgrade change for reliable CI |
| Web E2E / device mobile smoke | **UNVERIFIED** |
| Local 100% gate (50/56 PASS) | **Not re-audited** in this sprint |

## Mobile 3001 dependency removed?

**YES** in code — no silent `localhost:3001` fallback in `room-ready/lib/config.ts`.

## Production / go-live

**Out of scope** for Prompt 1. No deployment performed.

## Suggested next steps (Prompt 2+, not started)

- Browser E2E or role checklist for M10.1 **PASS**.
- Merge sprint branch to `develop` after review.
- Re-run feature audit row M10.1 with Auth0 evidence.