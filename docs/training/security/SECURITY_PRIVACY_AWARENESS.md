# Security & privacy awareness

## Login & MFA

- Use organisation Auth0 login only — no shared accounts.
- Complete MFA when prompted on staff accounts (`AUTH0_REQUIRE_MFA_CLAIM` in production target).

## Passwords & devices

- Unique strong passwords; password manager encouraged.
- Mobile: biometrics unlock session — still lock phone OS.
- **Lost device:** report in app → remote session revoke.

## Role permissions

- Access **need-to-know** only; audit logs record sensitive reads.
- UI hiding ≠ permission — API enforces isolation.

## Tenant data & documents

- Confidential documents in private S3 — download via app only.
- No emailing exports to personal accounts.

## GDPR (organisation duties)

- Data subject requests: `docs/phase7/privacy/DATA_SUBJECT_REQUEST_PROCEDURE.md`
- Retention: `docs/phase7/privacy/DATA_RETENTION_SCHEDULE_TEMPLATE.md`
- Breach: `docs/phase7/privacy/BREACH_RESPONSE_PROCEDURE.md`

## Phishing

- Verify sender before clicking Auth0 or HMore links; report suspicious login attempts.

## Incidents

- Safeguarding/incidents modules for operational reporting — follow local escalation policy.

## Training acknowledgement

Track completion in your LMS or sign-in sheet — **not** auto-recorded by HMore F7.8 materials alone.
