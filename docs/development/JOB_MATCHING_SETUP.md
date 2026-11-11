# Job matching setup (F5.4)

## Migrate

```bash
cd apps/api
alembic upgrade head
```

Expected head: `20261110_3700_f54`.

## Optional external job APIs

```env
JOB_SOURCE_ADZUNA_APP_ID=
JOB_SOURCE_ADZUNA_APP_KEY=
JOB_SOURCE_REED_API_KEY=
JOB_SOURCE_TIMEOUT_SECONDS=12
JOB_MATCH_LIVE_SEARCH_ENABLED=true
```

Without these keys, tenants still search organisation catalogue listings and staff structured imports. `GET /api/v1/job-matching/sources` reports availability.

## Optional AI explanations

Feature flag: `ai.agent.job_matching`  
Workflow: `job_match_explain`  
Search and scoring work when AI is disabled or capped.

## Staff import example

```http
POST /api/v1/job-matching/jobs/import
{
  "jobs": [{
    "external_id": "local-1",
    "title": "Retail assistant",
    "employer_name": "Local Shop",
    "location": "Birmingham",
    "employment_type": "part_time",
    "required_skills": ["Customer service"],
    "source_url": "https://example.com/jobs/local-1"
  }]
}
```

## Tests

```bash
cd apps/api
pytest tests/test_f54_job_matching.py -q -m "not postgres"
pytest tests/test_f54_job_matching.py -q -m postgres
```
