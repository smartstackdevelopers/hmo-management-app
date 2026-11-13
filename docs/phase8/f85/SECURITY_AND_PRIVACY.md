# Security and Privacy (F8.5)

- Organisation isolation via RLS (`hmore_org_isolation`) on all marketplace tables
- Contractors see assigned jobs only; tenant PII excluded from notifications
- Documents private via `file_metadata`; no public URLs
- Feedback stored with `moderation_status=pending` — not published by default
- Global and org gates required before any marketplace action
- Audit events for settings, registration, verification, jobs, quotations, assignment, completion

Pending: DPO sign-off on contact disclosure (`show_contact_to_landlords`) and retention policy for quotations/invoices.
