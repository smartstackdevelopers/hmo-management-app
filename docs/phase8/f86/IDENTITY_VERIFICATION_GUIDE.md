# Identity Verification Guide

Users submit identity files via existing private upload APIs, then `POST /identity/documents`. Administrators review with `POST /identity/{id}/review`. Optional `POST /identity/{id}/provider-check` creates sandbox provider requests only.

Statuses are never set to `verified` without an authorised reviewer or approved provider callback handling.
