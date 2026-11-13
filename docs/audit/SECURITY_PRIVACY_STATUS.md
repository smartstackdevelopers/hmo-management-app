# Security and privacy status (F7.10)

Consolidates F7.1 and F7.2 with F6.5 occupancy gate. **No legal sign-off claimed.**

## Security

| Control | Status | Evidence |
| --- | --- | --- |
| Authentication (Auth0 JWT) | **PASS** | `test_auth_*`, `test_f111_security_config.py` |
| MFA | **PARTIAL** | Enforced only when IdP + env claim enabled |
| Six-role RBAC | **PASS** | `test_rbac_registry.py`, matrix tests |
| Organisation isolation | **PARTIAL** | Strong tests; postgres marked in CI |
| API authz deny paths | **PASS** | Feature tests per module |
| Generic 401 bodies (F7.1 fix) | **PASS** | `test_auth_failure_response_is_generic` |
| File upload validation | **PASS** | `test_f18_storage.py` |
| Integration SSRF / Fernet | **PASS** | `test_f64_integration_hub.py`, F7.1 |
| Audit logging | **PASS** | `test_f17_audit.py` |
| Encryption in transit | **PARTIAL** | HTTPS required prod; local HTTP dev |
| Encryption at rest | **PARTIAL** | RDS/S3 SSE **PENDING APPROVAL** |
| Vulnerability testing | **PARTIAL** | F7.1 — no external pen test |
| Incident response | **PARTIAL** | F7.9 runbooks **PENDING APPROVAL** |
| Rate limiting | **PARTIAL** | Edge/WAF recommended residual |

### Outstanding security risks (F7.1 residuals)

- npm transitive vulnerabilities (no blind major upgrades)
- MFA off by default in dev; production operator-owned
- No app-level rate limits on all routes
- Occupancy device HMAC residual while live deferred

## Privacy

| Control | Status | Evidence |
| --- | --- | --- |
| GDPR/DPIA documentation | **PARTIAL** | `docs/phase7/privacy/`, F7.2 report |
| Privacy dashboard (DSAR, retention templates) | **PARTIAL** | `test_f72_privacy_management.py` |
| Data subject request workflow | **PARTIAL** | API blocks unsafe erasure without evidence |
| Breach response procedure | **PARTIAL** | F7.9 plan — DPO decision required |
| AI data processing review | **PASS** (doc) | `AI_DATA_PROCESSING_REVIEW.md` |
| AI human approval for writes | **PASS** | Housing/support plan draft tests |
| AI usage caps | **PASS** | `test_f33_ai_usage_caps.py` |
| Room occupancy privacy gate | **PASS** (technical) | Ingest 403; **DPIA PENDING APPROVAL** |
| Room occupancy — no facial recognition | **PASS** | Design + `test_f65` |
| Training security awareness | **PARTIAL** | Materials F7.8; delivery pending |
| WCAG / accessibility | **PARTIAL** | F7.5 axe e2e |

## Approvals not evidenced

| Item | Status |
| --- | --- |
| ICO/DPO breach process adoption | **PENDING APPROVAL** |
| Organisational retention schedule signed | **PENDING APPROVAL** |
| Room occupancy live DPIA | **BLOCKED** / gate incomplete |
| Production security sign-off | **PENDING APPROVAL** |
