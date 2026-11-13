# F7.9 documentation verification checklist

Use before claiming operational readiness (still requires **PENDING APPROVAL** from client).

| # | Check | Result |
| --- | --- | --- |
| 1 | Procedures match monorepo layout (web/api/ai/mobile) | ☐ |
| 2 | Commands marked destructive have warnings | ☐ |
| 3 | Recovery aligns with F7.3 `DATABASE_RESTORE_PROCEDURE.md` | ☐ |
| 4 | Security aligns with F7.1 report | ☐ |
| 5 | Privacy/breach aligns with F7.2 | ☐ |
| 6 | Deploy aligns with F7.6 infrastructure docs | ☐ |
| 7 | Escalation placeholders labelled CONFIG_PLACEHOLDER | ☐ |
| 8 | No secrets or real tenant PII in examples | ☐ |
| 9 | Markdown renders in repo | ☐ |
| 10 | Six roles only in access guide | ☐ |
| 11 | Room occupancy gate respected | ☐ |
| 12 | RPO/RTO not falsely claimed verified | ☐ |
| 13 | No invented training/drill completion | ☐ |
| 14 | `test_f79_runbooks.py` passes in CI | ☐ |

Automated: item 14 via pytest. Manual: items 1–13 before go-live adoption.
