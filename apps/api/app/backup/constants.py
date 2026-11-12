"""F7.3 backup and restore drill constants."""

from __future__ import annotations

BACKUP_TYPES = frozenset({"database", "files_manifest", "config_manifest"})
BACKUP_SCOPES = frozenset({"platform", "organisation"})
BACKUP_STATUSES = frozenset(
    {
        "pending",
        "running",
        "completed",
        "failed",
        "verifying",
        "verified",
        "rejected_incomplete",
    }
)
VERIFICATION_STATUSES = frozenset({"not_started", "passed", "failed"})
RETENTION_TIERS = frozenset({"daily", "weekly", "monthly"})
DRILL_STATUSES = frozenset({"pending", "running", "passed", "failed", "blocked"})
