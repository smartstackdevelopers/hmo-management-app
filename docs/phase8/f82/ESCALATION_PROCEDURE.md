# Escalation Procedure

Manual escalation: `POST /alerts/{id}/escalate` with `target_role` and optional `target_user_id`.

Organisation `escalation_targets` JSON configures overdue follow-up routing (no fixed SLA).

Escalation history stored in `safeguarding_alert_escalations` with acknowledgement fields.

Notifications use role-appropriate, non-sensitive preview text.
