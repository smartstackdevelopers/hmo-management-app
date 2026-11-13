# F8.11 Advanced Automation Architecture

Optional add-on layering **intelligent workflows** on **F6.3** (`/api/v1/automation`) and **F2.13** (`/api/v1/org-workflows` approvals inbox).

- API: `/api/v1/advanced-automation`
- Platform gate: `ADVANCED_AUTOMATION_GLOBAL_ENABLED=false`
- Organisation gate: `organisation_advanced_automation_settings.enabled`
- Versions: `intelligent_workflow_versions` — running executions pin `version_id`
- Test runs: `dry_run=true` — no live notifications
