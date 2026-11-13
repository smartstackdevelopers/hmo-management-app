# Super Admin — training guide

**Who:** Platform operators with `super_admin` role.  
**Home:** `/dashboard/super-admin`  
**Permissions:** See matrix — organisations, platform settings, monitoring, audit, privacy/backup/performance (Phase 7).

## 1. Platform dashboard

- Open **Dashboard home** then Super Admin home for org-wide summary widgets (as implemented on your deployment).
- **Do not** use UI visibility as security — API enforces RBAC.

## 2. Organisations

- **Organisations** (nav): create/read/manage organisations (`organisations.*`).
- Steps: list → select org → review membership and status.
- **Mistake:** Creating duplicate orgs — use consistent naming convention.

## 3. Users and roles

- Organisation Admins invite users; Super Admin can assign `super_admin` only with strict process.
- Use **role assignment** APIs via org admin workflows where exposed in UI.

## 4. Monitoring & performance

- **Performance** (`/dashboard/performance`): synthetic benchmarks — Super Admin only run.
- **Backups** / **Privacy** dashboards: Phase 7 operator tools — read reports before go-live decisions.

## 5. Audit & security

- **Audit** (`/dashboard/audit`): sensitive reads — export only for authorised investigations.
- Review F7.1 security report: `docs/phase7/F7.1_SECURITY_TESTING_REMEDIATION.md`.
- Enforce Auth0 MFA for staff accounts in Auth0 tenant policy.

## 6. AI usage

- **AI activity** / **AI costs** / **AI feature flags**: monitor caps; do not disable human approval requirements for agents.

## 7. FAQs

**Q: Why can I see a menu another role cannot?**  
A: Super Admin has the broadest permission set; tenants and contractors are intentionally restricted.

**Q: Can I access tenant medical notes?**  
A: Only if explicitly permitted and audited — default is deny by role design.

## Screenshot placeholders

Add staging captures: super-admin home, organisations list, audit view → `docs/training/assets/screenshots/super-admin/`.
