# Quotation Approval Guide

1. Approved contractors submit `POST /contractor-marketplace/quotations` with line costs — no auto-approval.
2. Landlords/org admins compare totals offline; approve with `POST /quotations/{id}/approve`.
3. Approval may auto-assign contractor when job unassigned.
4. Rejected quotations remain stored with status updates (future UI).

Tax amounts must be supplied by the contractor — the platform does not calculate tax automatically.
