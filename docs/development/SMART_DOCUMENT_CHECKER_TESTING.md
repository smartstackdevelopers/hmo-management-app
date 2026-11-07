# F3.6 document checker testing

## Unit (no database, no OCR engine, no LLM)

```bash
cd apps/api
pytest tests/test_f36_document_checks_unit.py -q

cd ../ai-service
pytest tests/test_document_check.py -q
```

## PostgreSQL

```bash
cd apps/api
pytest tests/test_f36_document_checks.py -m postgres -q
```

These tests use the in-memory private store and the local PDF text parser. The AI client is monkeypatched for budget and invalid-output cases. They do not call OpenAI or an OCR binary.

## Frontend

```bash
cd apps/web
npx playwright test e2e/document-checks.spec.ts
```

## What was not tested as a live integration

- Tesseract or any image OCR
- OpenAI
- Redis cache hits
- Celery execution of a document check
