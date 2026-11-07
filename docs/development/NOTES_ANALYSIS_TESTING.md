# F3.4 Notes Analysis testing

## Unit (no database)

```bash
cd apps/api
pytest tests/test_f34_notes_analysis_unit.py -q

cd ../ai-service
pytest tests/test_notes_analysis.py -q
```

## PostgreSQL

```bash
cd apps/api
pytest tests/test_f34_notes_analysis.py -m postgres -q
```

Requires `TEST_DATABASE_URL` / `DATABASE_URL`.

## Distinctions

| Suite | Kind |
| --- | --- |
| Heuristic / schema / RBAC | Unit |
| AI workflow with `LLM_PROVIDER=none` | Mocked / local heuristic |
| Postgres service tests | Real PostgreSQL |
| Real OpenAI | Not required for acceptance |

Never report heuristic runs as real provider billing.
