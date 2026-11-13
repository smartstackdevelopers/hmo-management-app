# F8.5 Testing Report

## Automated

- `apps/api/tests/test_f85_contractor_marketplace.py` — categories, RBAC, alembic head, docs presence
- Alembic head: `20261117_5300_f85`
- Existing suite head assertions updated

## Manual (required before production)

- Registration → verification → marketplace search (approved only)
- Job + quotation + approval + assignment
- Completion + review + verified status
- Permission matrix for six roles
- Mobile workspace job list
- Org isolation spot checks

Use synthetic contractors and test properties only.
