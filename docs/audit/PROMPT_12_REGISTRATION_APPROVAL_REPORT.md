# PROMPT 12 — Registration & Approval Report

| Status | **PARTIAL** |

## Implemented

| Requirement | Status |
| --- | --- |
| Registration form fields (name, email, phone, password, role, org, consent) | **PASS** (web + API) |
| No self-register as super_admin | **PASS** |
| No public organisation_admin self-register | **PASS** |
| Pending account status | **PASS** (code) |
| Requested role stored separately | **PASS** (`registration_requests.requested_role`) |
| Approval notifications (in-app) | **PASS** (code) |
| Approve / reject with audit | **PASS** (code) |
| Self-approval prevention | **PASS** |
| Org Admin cannot approve Org Admin | **PASS** |
| Super Admin create Org Admin | **PASS** (`POST /auth/users/organisation-admin`) |
| Pending users blocked from protected API | **PASS** (`identity._assert_account_may_access`) |

## Evidence

- Service: `app/auth/native_service.py`
- API: `app/api/v1/native_auth.py`
- Web: `/register`, `/register/pending`, `/dashboard/approvals/registrations`
- Unit: public role policy covered in `test_p12_native_auth_unit.py`

## Blockers

| Item | Status |
| --- | --- |
| Live DB migration + browser E2E of approve journey | **BLOCKED** (Postgres/Docker down) |
| Email/SMS delivery of approvals | **UNVERIFIED** — intentionally in-app only; providers not configured |

## Status

**PARTIAL**
