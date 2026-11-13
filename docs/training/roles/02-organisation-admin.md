# Organisation Admin — training guide

**Who:** `organisation_admin` for one active organisation.  
**Home:** `/dashboard/organisation-admin`

## Core modules (web)

| Topic | Navigation | Permissions (examples) |
| --- | --- | --- |
| Staff & users | Organisation workflows / users | `organisation.users.*` |
| Tenants & housing | Tenants, housing applications, waiting list | `tenants.*`, `housing.*` |
| Properties & rooms | Properties, Rooms | `properties.*`, `rooms.*` |
| Approvals | Org workflows → approvals | workflow permissions |
| Documents | Documents hub | `documents.*` |
| Communications | Communications | `communication.*` |
| Reports | Reports hub, schedules, alerts | `reports.*` |
| Maintenance & complaints | Maintenance, Complaints | module permissions |
| Compliance | Training, safeguarding, incidents | compliance permissions |
| Audit | Audit (org-scoped) | `audit_logs.read` |
| Automation | Automation rules | F6.3 |
| Integrations | Integration hub | F6.4 (secrets via env) |

## Workflow: housing application review

1. Open **Housing applications**.
2. Open application detail — review evidence packs.
3. Use **AI housing analysis** only as advisory — **you** approve/reject in workflow.
4. Record decision in audit trail (automatic via API).

**Common mistake:** Approving without reading evidence documents.

## Workflow: invite staff

1. Organisation Admin → user management (as exposed in your build).
2. Assign correct role (Support Worker, Landlord, etc.).
3. Confirm Auth0 invitation email sent.

## Reports

- Open `/dashboard/reports` — occupancy, housing, complaints, caseload, plans.
- Exports may contain personal data — handle under GDPR (F7.2).

## Security

- Do not share Organisation Admin credentials.
- Review DPIA pack: `docs/phase7/privacy/`.

## FAQs

**Q: Tenant cannot see a module on mobile?**  
A: Check role = `tenant` and organisation feature flags.

## Screenshots

`docs/training/assets/screenshots/org-admin/` — dashboard, housing list, reports.
