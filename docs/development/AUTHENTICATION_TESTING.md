# Authentication testing

## Automated (mocked) tests

Location: `apps/api/tests/test_auth_tokens.py`

These tests generate an ephemeral RSA key pair, serve a mocked JWKS document, and sign access tokens locally. They prove FastAPI rejection and acceptance rules without calling Auth0.

Covered cases:

- Valid token accepted
- Missing Authorization header rejected
- Invalid signature rejected
- Wrong issuer rejected
- Wrong audience rejected
- Expired token rejected
- MFA claim required when configured

Run:

```text
cd apps/api
pytest -q tests/test_auth_tokens.py tests/test_health.py
```

These tests are **not** evidence that a production Auth0 tenant works.

## Real tenant tests (manual)

Prerequisites: UK/EU Auth0 tenant configured per `IDENTITY_PROVIDER_SETUP.md` and MFA per `MFA_CONFIGURATION.md`.

| Step | Expected |
| --- | --- |
| Web `/auth/login` | Redirects to Auth0 |
| Staff MFA | Auth0 prompts for second factor |
| `/account` | Shows authenticated subject/email from session |
| API `/api/v1/auth/me` with access token | 200 and user row with `external_subject` |
| Tampered Bearer token | 401 |
| Logout | Session cleared; protected page redirects |

Record the date, tenant domain (not secrets), and tester name when this passes. Until then, mark F1.3 MFA and live integration **IMPLEMENTED BUT UNVERIFIED**.

## Web CI

GitHub Actions builds the Next.js app with placeholder Auth0 environment variables so the SDK can initialise. Placeholders are not a working tenant.
