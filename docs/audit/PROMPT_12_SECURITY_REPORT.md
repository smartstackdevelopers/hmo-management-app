# PROMPT 12 — Security Report

| Status | **PARTIAL** |

## Controls implemented

| Control | Status | Notes |
| --- | --- | --- |
| Argon2id password hashing | **PASS** | `app/auth/passwords.py` |
| No plaintext passwords | **PASS** | |
| Short-lived access tokens | **PASS** | default 900s |
| Refresh token rotation | **PASS** | old hash revoked + replaced |
| Refresh revocation on logout/password change | **PASS** | |
| Login throttling / lockout | **PASS** | failed_login_count + locked_until |
| Role from DB not client | **PASS** | RBAC unchanged |
| Pending/rejected/suspended blocked | **PASS** | |
| Auth0 disabled by default | **PASS** | `HMORE_ALLOW_AUTH0=false` |
| Secrets via env | **PASS** | `HMORE_NATIVE_AUTH_SECRET` |
| CSRF for cookie SPA mutations | **PARTIAL** | Web uses HttpOnly cookies + server actions; dedicated CSRF token not added |
| Native MFA | **UNVERIFIED** | Auth0 `amr` MFA not replaced; staff MFA follow-up |

## Findings

1. **Positive:** Auth0 is no longer required for token validation when native auth is enabled.  
2. **Positive:** Registration privilege escalation paths are rejected server-side.  
3. **Risk:** Default native secret must be changed before any production use (validator enforces non-default in production).  
4. **Risk:** Demo auth remains available in development — keep gated.  
5. **Follow-up:** Add explicit CSRF tokens if cookie session is used for browser `fetch` mutations outside server actions.

## Tests executed

- `pytest tests/test_p12_native_auth_unit.py` → **5 passed**

## Status

**PARTIAL**
