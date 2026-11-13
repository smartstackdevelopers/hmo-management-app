# Contractor Registration Guide

1. Enable org marketplace after privacy review (`PATCH /contractor-marketplace/settings`).
2. Contractor user (Maintenance & Contractors role) submits `POST /contractor-marketplace/register`.
3. Status moves from `draft` to `submitted` — not visible in public marketplace until approved.
4. Upload insurance and qualifications via existing file APIs; attach as `contractor_documents` (admin linking in follow-up UI).

Do not mark contractors as verified without administrator review.
