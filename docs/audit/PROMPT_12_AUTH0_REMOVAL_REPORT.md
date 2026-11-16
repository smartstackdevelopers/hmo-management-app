# PROMPT 12 — Auth0 Removal Report

| Status | **PARTIAL** |

## Active path changes

| Item | Classification |
| --- | --- |
| API `validate_access_token` | Auth0 branch only if `HMORE_ALLOW_AUTH0=true` (**off**) |
| Web `Auth0Client` construction | **Removed** from active path; shim uses native cookies |
| Web middleware Auth0 | **No-op** |
| Mobile default mode | **native** (not Auth0) |
| `@auth0/nextjs-auth0` package | Still in `package.json` — **unused config remnant** until deleted after smoke |
| `room-ready/lib/hmoreAuth0.ts` | Retained for token storage helpers / optional legacy; not default login |
| Docs/training mentioning Auth0 | **Historical documentation** |

## Remaining Auth0 references

| Class | Action |
| --- | --- |
| Active dependency | None for default local auth |
| Compatibility / storage helpers | Keep short-term (`hmoreAuth0` token keys) |
| Historical docs | Leave; do not treat as runtime |
| Optional re-enable flag | `HMORE_ALLOW_AUTH0` — stakeholder default **false** |

## Hidden Auth0 login fallback?

**No** for default env: native/demo only. Auth0 login UI is not the mobile/web default.

## Status

**PARTIAL** — package uninstall and doc sweep remain after DB-backed E2E green.
