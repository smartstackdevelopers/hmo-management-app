# Data Synchronisation Guide (F8.9)

Scheduled, manual, and incremental sync remain in F6.4 (`integrations/sync.py`, sync jobs table). F8.9 dashboard surfaces recent activity from existing `IntegrationActivityLog` and sync job records.

Conflict detection and incremental cursors are PARTIAL — extend F6.4 sync engine rather than duplicating logic.