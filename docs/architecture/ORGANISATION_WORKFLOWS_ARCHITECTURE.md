# F2.13 Organisation workflows

## Scope

- **Approvals inbox**: read-only aggregation over existing module records (housing, document access, maintenance, complaints, evidence, custom form submissions). Decisions delegate to the source module services — no duplicate approval rows.
- **Workflow configuration**: versioned JSON step definitions per organisation (`org_approval_workflows`, `org_approval_workflow_versions`).
- **Custom forms**: versioned schemas (`org_custom_forms`, `org_custom_form_versions`) and submissions (`org_custom_form_submissions`).
- **Secure sharing**: expiring grants with SHA-256 token hashes (`secure_sharing_grants`, `secure_sharing_access_logs`).
- **Audit UI**: uses existing `GET /api/v1/audit-events` (F1.7).

## API

Base path: `/api/v1/org-workflows`

See `apps/api/app/api/v1/org_workflows.py` for routes.

## RBAC

Permissions are defined in `apps/api/app/rbac/permissions.py` (prefixes `approvals.*`, `organisation.forms.*`, `secure_sharing.*`). Organisation isolation uses PostgreSQL RLS on all new tables.

## Limitations

- Not a full BPM engine; workflow steps are configuration snapshots only.
- Complaint and evidence inbox items link to source records for decisions (no bypass of module rules).
- Form builder UI is list/preview oriented; full visual builder is out of scope.
