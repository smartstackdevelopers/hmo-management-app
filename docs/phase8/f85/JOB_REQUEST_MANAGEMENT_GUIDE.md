# Job Request Management Guide

Authorised users with `contractor_marketplace.manage`:

1. Create `POST /contractor-marketplace/jobs` with `property_id`, description, optional `maintenance_request_id`.
2. Set `quotations_requested=true` to enter quotation workflow.
3. Assign directly with `POST /jobs/{job_id}/assign/{profile_id}` only when no conflicting assignment exists.

Status flow: `requested` → `quotation_pending` → `quotation_received` → `assigned` → `in_progress` → `completed` → `verified`.
