# F8.11 API Endpoints

Base: `/api/v1/advanced-automation`

| Method | Path | Permission |
|--------|------|------------|
| GET | `/dashboard` | read |
| GET/POST | `/workflows` | read / manage |
| PUT | `/workflows/{id}/draft` | manage |
| POST | `/workflows/{id}/publish` | manage |
| POST | `/workflows/{id}/test-run` | execute |
| GET | `/executions` | reports |
| GET | `/approvals/pending` | approve |
| POST | `/approvals/{id}/decide` | approve |
| POST | `/ai/suggest` | ai |
