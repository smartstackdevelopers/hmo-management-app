# Job matching architecture (F5.4)

Search-first AI job matching for HMore tenants using F5.3 skills/CV data, approved job sources, local embeddings and optional AI explanations.

## Processing order

1. Structured / keyword search against `job_listings` (org-scoped).
2. Live refresh from Adzuna / Reed when credentials exist (official APIs only).
3. Hashing-trick embeddings + cosine ranking (no separate vector DB).
4. Transparent relevance score (skills, interests, type, location, semantic).
5. Optional AI explanation via `job_match_explain` (`ai.agent.job_matching`) — never invents vacancies.

## Sources

| Source | Access |
| --- | --- |
| `hmore_catalogue` | Published `OpportunityListing` jobs/training |
| `structured_import` | Staff JSON import |
| `adzuna` | `JOB_SOURCE_ADZUNA_APP_ID` + `JOB_SOURCE_ADZUNA_APP_KEY` |
| `reed` | `JOB_SOURCE_REED_API_KEY` |

Missing credentials are reported; search remains useful from catalogue/import.

## Tables

`job_listings`, `training_opportunities`, `tenant_job_match_preferences`, `tenant_job_matches`, `tenant_saved_jobs`, `tenant_saved_training`.

## Integration

- Profile from F5.3 assessment + selected CV.
- Tracker via F5.3 `create_application` (cannot mark Applied automatically).
- Staff progress on employment-support dashboard (no private CV dump).
