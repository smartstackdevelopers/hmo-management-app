# PROMPT 12 — Test Report

| Suite | Result | Notes |
| --- | --- | --- |
| `pytest tests/test_p12_native_auth_unit.py` | **PASS** (5) | hashing, tokens, role policy |
| Full API pytest | **UNVERIFIED** | Postgres unavailable |
| Web Playwright | **UNVERIFIED** | not run this sprint |
| Mobile Jest | **UNVERIFIED** | not run this sprint |
| Browser E2E registration→approval→login | **BLOCKED** | Docker/Postgres down |

## Planned integration cases (code ready, DB required)

Registration, duplicate email, invalid role, super_admin self-reg deny, approval, rejection, self-approval deny, login pending/rejected/suspended, refresh rotation, lockout.

## Status

**PARTIAL**
