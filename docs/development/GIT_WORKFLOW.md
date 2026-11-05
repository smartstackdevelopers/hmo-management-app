# Git workflow

Permanent Git governance for HMore. This supplements HMore Proposal-Exact Complete Implementation Plan v1.0. It does not change that plan.

Source of truth for product scope remains the implementation plan. Branch families in that plan (`feature/phaseN-*`, `chore/phaseN-*`, `release/1.0*`) are the names used here.

Verified on 2026-11-05. This document does not mean branch protection or CI is already turned on. See the status section.

## Branch responsibilities

| Branch | Role |
| --- | --- |
| `main` | Production-ready code only. No direct development. Protected. |
| `develop` | Integration and testing. Must stay buildable. Feature work lands here only through a pull request. |
| `feature/phaseN-feature-name` | New functionality. Created from `develop`. |
| `chore/phaseN-task-name` | Infrastructure, configuration, and maintenance. Created from `develop`. |
| `bugfix/phaseN-description` | Non-production bug fixes. Created from `develop`. |
| `release/1.0.0` | Release preparation and final QA. Created from `develop` when a release is approved. |
| `hotfix/description` | Urgent production fixes. Created from `main`. |

`N` is the phase number from the plan, 1 through 7.

## Official flow

```text
develop
  → create feature or chore branch
  → implement
  → run tests
  → commit
  → push that branch
  → pull request into develop
  → CI checks
  → code review
  → merge into develop
  → integration, regression, and end-to-end testing
  → release branch
  → final QA
  → approved merge into main
```

Do not commit on `main` or `develop`. Do not push feature work straight to `main`. Do not merge without review. Do not skip CI once those checks exist.

## Examples by phase

Phase 1:

- `feature/phase1-auth`
- `feature/phase1-database`
- `feature/phase1-rbac`
- `feature/phase1-multitenancy`
- `feature/phase1-core-crud`
- `chore/phase1-monorepo`
- `chore/phase1-cicd`
- `chore/phase1-project-audit`

Phase 2:

- `feature/phase2-support-management`
- `feature/phase2-housing-cases`
- `chore/phase2-celery-redis`

Phase 3: `feature/phase3-ai-gateway`, `feature/phase3-notes-analysis`, `chore/phase3-usage-caps`

Phase 4: `feature/phase4-tenant-app`, `feature/phase4-staff-app`, `chore/phase4-eas`

Phase 5: `feature/phase5-community-directory`, `feature/phase5-jobs-skills`

Phase 6: `feature/phase6-analytics`, `feature/phase6-occupancy` (only after the DPIA gate)

Phase 7: `release/1.0.0`, `chore/phase7-runbooks`

Same pattern for any later item: `feature/phaseN-short-name` or `chore/phaseN-short-name`. Use lowercase words separated by hyphens.

## Feature workflow

```text
git fetch origin
git checkout develop
git pull origin develop
git checkout -b feature/phase1-auth
```

Implement only the feature named in the branch. Run the tests that exist for that area. Commit. Push the feature branch. Open a pull request into `develop`.

## Chore workflow

Same as a feature branch, with a `chore/phaseN-...` name. A chore does not add product behaviour. Monorepo layout and GitHub Actions belong on chore branches such as `chore/phase1-monorepo` and `chore/phase1-cicd`.

## Pull requests

Every pull request targets `develop`, except an approved release merge into `main` or a hotfix.

The description must include:

- Purpose of the change
- Feature ID (for example F1.3)
- Files modified
- Security impact
- Database impact
- Tests executed
- Test results
- Acceptance criteria
- Remaining issues

Merge only after review and after the required CI checks are green. Those checks are not configured yet. Do not treat a missing check as a pass.

## Merge strategy

- Feature and chore branches merge into `develop` with a merge commit or squash, as the reviewer chooses, after CI and review.
- `develop` moves to a `release/*` branch for final QA. That release merges into `main` only after approval.
- Fast-forward `develop` to `main` only when the histories have not diverged and a person has approved it. Do not force the merge.
- Hotfix: branch from `main`, pull request back into `main`, then merge the same fix into `develop` so the branches do not drift.

## Commit messages

Conventional Commits:

```text
feat(phase1): add authentication foundation
fix(phase1): resolve permission validation
chore(phase1): configure GitHub Actions
docs(phase1): update architecture documentation
test(phase1): add organisation isolation tests
```

Subject line states why the change exists. Do not commit `.env` files, keys, or seed passwords.

## Testing

Before a pull request, run the checks that already exist for the files you touched. Today the repo has no Pytest, Playwright, or GitHub Actions run, so "tests passed" must not be claimed until a command has actually been run and its result is pasted in the pull request.

When F1.1 adds CI, pull requests into `develop` must run:

- Python formatting and lint
- Pytest
- TypeScript type check
- Frontend lint
- Playwright
- API integration tests
- Build
- Dependency review
- Secret scanning

Do not add a workflow that always succeeds. Implementing that workflow is the F1.1 task, not this document.

## Release process

1. `develop` is buildable and the phase exit checklist is met.
2. Create `release/1.0.0` from `develop`.
3. Final QA on that branch only. Fixes land on the release branch as `fix(...)` commits, then merge back to `develop`.
4. Approved pull request from `release/1.0.0` into `main`.
5. Tag the merge on `main` only when the release is accepted. Do not tag from a feature branch.

## Hotfix process

1. `git checkout main` then `git checkout -b hotfix/short-description`.
2. Smallest change that fixes the production fault, with a test.
3. Pull request into `main`. After it is merged, open a second pull request into `develop` with the same fix.
4. Do not rebuild unrelated features on a hotfix branch.

## Conflicts

1. Stop if the conflict is on `main` or `develop` and you did not expect it.
2. On a feature branch, merge `origin/develop` into the feature branch. Do not rebase a branch that has already been pushed.
3. Resolve conflicts in the feature branch, run tests, and push the feature branch.
4. Do not use `git reset --hard`, `git clean -fd`, or force push to drop the other side.

## Safety rules

- Inspect the branch and `git status` before any Git command.
- Do not discard uncommitted files.
- Do not rewrite shared history or delete existing branches.
- Do not force push.
- Do not commit secrets.
- Do not push directly to `main`.
- Do not merge an unreviewed feature branch.
- If the working tree is dirty, do not switch branches until the files are committed on the correct branch or the situation is reported.

## Future implementation prompts

Every later HMore prompt must name:

- Current phase
- Feature ID
- Required branch
- The implementation plan as source of truth
- Stack limits (FastAPI, Next.js, Expo, PostgreSQL, separate AI service)
- Security requirements for that feature
- Tests required
- Acceptance criteria
- Docs to update
- Commit and pull request steps

Do not start the next phase in the same prompt.

## Branch protection to configure

Applied on 2026-11-05 through the GitHub branch protection API. GitHub CLI is still not installed. Status checks are not required yet, because no GitHub Actions workflow exists. Requiring a missing check would block every pull request.

`main`:

- Pull request required
- One approval required
- Force push blocked
- Deletion blocked
- Rules apply to administrators

`develop`:

- Pull request required
- Force push blocked
- Deletion blocked
- Rules apply to administrators

After F1.1 adds a workflow and a run is visible, add that workflow as a required status check on both branches.

## Current synchronization

Executed after explicit approval. No force push. `main` was not pushed.

| Ref | Commit |
| --- | --- |
| `main` and `origin/main` | `f0a1625` Add the implementation plan and Smart Vite prototype spec to docs. |
| `develop` and `origin/develop` | `f0a1625` after fast-forward `d889dbc..f0a1625` |
| `origin/docs/prototype-spec` | `f0a1625` |

`origin/develop` and `origin/main` now point at the same commit. Audit and governance documents stay on `chore/phase1-git-governance` until that pull request merges into `develop`.

Do not commit those documents directly on `main` or `develop`.
