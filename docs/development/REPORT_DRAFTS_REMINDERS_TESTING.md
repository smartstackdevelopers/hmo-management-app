# F3.13 testing

## Unit

```powershell
cd apps/api
python -m pytest tests/test_f313_report_drafts_unit.py -q
```

```powershell
cd apps/ai-service
python -m pytest tests/test_report_draft_narrative.py -q
```

## PostgreSQL

```powershell
cd apps/api
python -m pytest tests/test_f313_report_drafts.py -m postgres -q
```

Covers draft generation without AI, human approve without distribution, tenant denial, cross-org isolation, and ReminderRecord overdue dedupe.

## Frontend helpers

```powershell
cd apps/web
npx playwright test e2e/report-drafts.spec.ts
```
