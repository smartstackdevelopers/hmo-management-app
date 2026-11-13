# F8.9 Testing Report

| Area | Status | Notes |
|------|--------|-------|
| RBAC six roles | PASS | `test_f89_integration_hub.py` |
| Webhook HMAC | PASS | unit tests |
| Alembic head | PASS | `20261121_5700_f89` |
| API integration tests | PARTIAL | sandbox data; live providers BLOCKED |
| Organisation isolation | PARTIAL | RLS migration; re-use F6.4 SSRF tests |
| Performance | PENDING APPROVAL | load tests not run |

Use synthetic data only for connector and webhook scenarios.