# Production acceptance checklist (F7.12)

Consolidates Prompt 11 Go-Live §16 with current evidence.

| # | Criterion | Status |
| --- | --- | --- |
| 1 | Production web accessible | **FAIL** — not deployed |
| 2 | Backend APIs operational | **FAIL** — not deployed |
| 3 | AI service operational | **FAIL** — not deployed |
| 4 | PostgreSQL healthy (prod) | **FAIL** |
| 5 | Redis + Celery healthy (prod) | **FAIL** |
| 6 | Private S3 works | **FAIL** |
| 7 | Monitoring active (prod) | **FAIL** |
| 8 | Backups configured (prod) | **FAIL** |
| 9 | Authentication (prod) | **NOT VERIFIED** |
| 10 | Six-role permissions (prod) | **NOT VERIFIED** |
| 11 | Organisation isolation (prod) | **NOT VERIFIED** |
| 12 | Critical journeys (prod) | **NOT VERIFIED** |
| 13 | Mobile prod API | **NOT VERIFIED** |
| 14 | Operational docs | **PASS** |
| 15 | Security/privacy approvals recorded | **FAIL** |

**Production acceptance:** **FAIL**  
**Staging/CI acceptance:** **PARTIAL** — automated tests green on `develop`
