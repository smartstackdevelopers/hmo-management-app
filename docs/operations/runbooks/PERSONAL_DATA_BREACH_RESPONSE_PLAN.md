# Personal data breach response plan

**Status:** Prepared template for data controllers. **HMore does not make legal reporting decisions.**

Supersedes the short F7.2 template for operational use; keep legal ownership with the **Data Protection Officer (DPO)** or responsible legal team (**CONFIG_PLACEHOLDER — DPO**).

Reference: UK GDPR Articles 33–34 (ICO notification within **72 hours** where required — assessment by DPO, not software).

## Important distinctions

- **Not every security incident** is a personal data breach.
- **Not every breach** is reportable to the ICO or individuals.
- Software supports registration, audit, and privacy workflows — **notification is outside the application**.

## 1. Breach identification

Sources: staff reports, Auth0 anomalies, Sentry (scrubbed), backup/access audits, data subject complaints, third-party processor notice.

Register internally in ticketing **CONFIG_PLACEHOLDER** and, where appropriate, HMore safeguarding/privacy modules.

## 2. Incident registration

| Field | Guidance |
| --- | --- |
| Reference ID | External ticket + optional HMore incident link |
| Discovery time | UTC timestamp |
| Reporter | Role — no real tenant names in examples |
| Preliminary type | Confidentiality / integrity / availability |

## 3. Nature of affected data

Document categories (e.g. contact details, case notes, documents, housing application). Use organisation records — export via authorised privacy/DSAR tools only.

## 4. Affected individuals

Count **where known**; if unknown, record estimation method and uncertainty.

## 5. Organisations affected

Which `organisation_id` values — cross-org breach is Critical severity.

## 6. Risk assessment (DPO-led)

| Factor | Notes |
| --- | --- |
| Sensitivity | Special category if applicable |
| Likelihood of harm | DPO judgement |
| Mitigations already applied | Encryption, access control, MFA |

**Software does not output “reportable: yes/no”.**

## 7. Containment actions

1. Revoke access (membership, sessions, API keys).
2. Block egress path (misconfigured bucket, stolen token).
3. Preserve logs — see SECURITY plan.
4. Room occupancy: ensure live ingest remains off if gate incomplete.

## 8. Evidence preservation

- `audit_events`, backup run metadata, access logs.
- Chain of custody for exports — external legal advice **PENDING APPROVAL**.

## 9. DPO notification

Notify **CONFIG_PLACEHOLDER — DPO** without undue delay after initial assessment.

## 10. Legal review

**CONFIG_PLACEHOLDER — Legal** reviews ICO and individual notification need.

## 11. ICO reporting assessment (UK)

Within **72 hours** of becoming aware of a breach **likely to result in risk** — DPO determines:

- Whether to notify ICO
- Content of notification
- Whether delay extension applies

HMore provides timestamps and audit exports to support the decision — **not** the decision itself.

## 12. Individual notification assessment

If **high risk** to rights and freedoms — DPO decides direct communication to data subjects.

## 13. Incident closure

| Closure item | Owner |
| --- | --- |
| Root cause summary | Technical |
| Corrective actions | Technical + DPO |
| DPIA / policy updates | DPO |
| Training refresh | Organisation (`docs/training/security/`) |

Record closure in external register; link HMore records if used.

## Related procedures

- `docs/phase7/privacy/DATA_SUBJECT_REQUEST_PROCEDURE.md`
- `docs/phase7/privacy/DATA_RETENTION_SCHEDULE_TEMPLATE.md`
- Dashboard → Privacy (F7.2) for DPIA and gate status
