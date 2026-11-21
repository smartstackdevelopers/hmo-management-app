# PROMPT 6 — Automation rules (Celery / Redis)

| Field | Value |
| --- | --- |
| Date | 2026-11-14 |
| Branch | `develop` @ `60b2f02` |

## Summary

| Criterion | Status |
| --- | --- |
| F8.11 advanced automation module | **PASS** (unit) — triggers, templates, validation, RBAC |
| Org context / no auto housing decisions | **PASS** (design) — triggers are operational (maintenance, documents, training); `ADDON_DISCLAIMER` requires human approval / F6.3 delegation; no housing-allocation automation found in `advanced_automation/` |
| Celery beat registration | **PASS** — `test_f68_phase6_celery_beat.py` includes `dispatch-automation-rules-every-5-minutes` |
| Live Redis/Celery runtime | **UNVERIFIED** — beat test does not connect to broker (by design) |

**Automation completion:** **~80%** — code + unit smoke **PASS**; worker/Redis E2E **UNVERIFIED**.

## Workers

| Component | Path |
| --- | --- |
| Celery app | `apps/api/app/workers/celery_app.py` |
| Tasks | `apps/api/app/workers/tasks.py` |
| Service | `apps/api/app/advanced_automation/service.py` |

## Tests executed

| File | Passed | Skipped | Failed |
| --- | ---: | ---: | ---: |
| `test_f811_advanced_automation.py` | 11 | 0 | 0 |
| `test_f68_phase6_celery_beat.py` | 1 | 0 | 0 |

## Gaps

- Optional local: `docker compose` Redis + single worker smoke (`dispatch_due_rules`).
- Document that integration hub auto-sync beat entry exists but hub is **not** mandatory core (Task 10).