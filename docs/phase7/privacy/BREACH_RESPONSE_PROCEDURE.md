# Personal data breach response procedure (template)

**Status:** Short pointer — full operator procedure: [`docs/operations/runbooks/PERSONAL_DATA_BREACH_RESPONSE_PLAN.md`](../operations/runbooks/PERSONAL_DATA_BREACH_RESPONSE_PLAN.md) (F7.9).

Operational and legal steps must be owned by the data controller. HMore provides audit logs and access controls; it does not detect breaches automatically.

## 1. Identify and contain

- Revoke compromised credentials; use device session revocation (F4.6) where applicable.
- Preserve audit logs (`audit_events`) — do not delete production data.

## 2. Assess risk to individuals

- Document in the organisation privacy risk register (Dashboard → Privacy).

## 3. Notify

- ICO / affected individuals per UK GDPR — **outside** HMore software.

## 4. Record

- Link incident to safeguarding/incident module where appropriate.
- Record breach handling notes in organisation policies (external document store).

## 5. Post-incident

- Update DPIA or technical safeguards as required.
- Review F7.1 security residuals.
