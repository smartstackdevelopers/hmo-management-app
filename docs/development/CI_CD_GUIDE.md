# CI/CD guide

Workflow file: `.github/workflows/ci.yml`

Runs on pull requests to `develop` and `main`, and on pushes to `develop`, `main`, `chore/phase1-*`, and `feature/phase1-*`.

## Jobs

| Job | What it runs |
| --- | --- |
| Web | `npm ci`, Next lint, `tsc --noEmit`, `next build`, Playwright Chromium smoke tests |
| Mobile | `npm ci`, `tsc --noEmit` in `room-ready` |
| API | `pip install -r apps/api/requirements.txt`, `compileall`, Pytest |
| AI | `pip install -r apps/ai-service/requirements.txt`, `compileall`, Pytest |

Node and pip caches are enabled.

A job that does not run these commands is not a pass. There is no dummy success step.

## Local equivalent

See `docs/development/LOCAL_SETUP.md`. If CI fails, fix the check. Do not skip it unless the job documents a missing runner capability.

Playwright in CI uses `next start` after `next build`. Locally it can reuse `next dev`.
