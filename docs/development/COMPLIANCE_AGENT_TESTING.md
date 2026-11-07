# F3.9 Compliance Agent — testing

## Unit (no DB)

```powershell
cd apps/api
python -m pytest tests/test_f39_compliance_agent_unit.py -q
```

## PostgreSQL integration

Requires `DATABASE_URL`. Skipped locally when unset.

```powershell
cd apps/api
python -m pytest tests/test_f39_compliance_agent.py -q
```

## AI service (mocked provider)

```powershell
cd apps/ai-service
python -m pytest tests/test_compliance_explanation.py -q
```

## Frontend helpers

```powershell
cd apps/web
npx playwright test e2e/compliance-agent.spec.ts
```

## Safety expectations

- AI explanation validator rejects legal-certification language.
- Sweep with AI budget exhaustion still returns deterministic findings (`ai_status=skipped_budget`).
- Review/resolve does not mutate `staff_training_records` or other source tables.
- Cross-organisation sweep/finding access is denied.
