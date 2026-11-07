from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from app.approval.models import ApprovalRecord, ApprovalStatus, ProposedAction
from app.context.trusted import TrustedCallerContext
from app.core.errors import ForbiddenError, ValidationServiceError, WorkflowError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalService:
    """In-memory approval gate foundation for future agents (not a full inbox UI)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, ApprovalRecord] = {}

    def create_pending(
        self,
        *,
        ctx: TrustedCallerContext,
        action_type: str,
        summary: str,
        payload: dict,
        workflow_id: str,
    ) -> ApprovalRecord:
        record = ApprovalRecord(
            approval_id=str(uuid.uuid4()),
            status=ApprovalStatus.pending,
            proposed_action=ProposedAction(
                action_type=action_type,
                summary=summary,
                payload=payload,
                organisation_id=ctx.organisation_id,
                proposed_by_workflow=workflow_id,
                created_at=_utcnow(),
                source="ai_suggestion",
            ),
        )
        with self._lock:
            self._records[record.approval_id] = record
        return record

    def get(self, approval_id: str, ctx: TrustedCallerContext) -> ApprovalRecord:
        with self._lock:
            record = self._records.get(approval_id)
            if not record:
                raise WorkflowError(f"Approval '{approval_id}' not found", status_code=404)
            if record.proposed_action.organisation_id != ctx.organisation_id:
                raise ForbiddenError("Approval belongs to another organisation")
            return record

    def decide(
        self,
        *,
        approval_id: str,
        ctx: TrustedCallerContext,
        approve: bool,
        note: str | None = None,
    ) -> ApprovalRecord:
        with self._lock:
            record = self.get(approval_id, ctx)
            if record.status != ApprovalStatus.pending:
                raise ValidationServiceError("Approval already decided")
            # AI cannot approve itself: reviewer must be the authenticated human user.
            updated = record.model_copy(
                update={
                    "status": ApprovalStatus.approved if approve else ApprovalStatus.rejected,
                    "reviewer_user_id": ctx.user_id,
                    "decision_note": note,
                    "decided_at": _utcnow(),
                }
            )
            self._records[approval_id] = updated
            return updated


_APPROVALS: ApprovalService | None = None
_APPROVALS_LOCK = threading.Lock()


def get_approval_service() -> ApprovalService:
    global _APPROVALS
    with _APPROVALS_LOCK:
        if _APPROVALS is None:
            _APPROVALS = ApprovalService()
        return _APPROVALS


def reset_approval_service_for_tests() -> ApprovalService:
    global _APPROVALS
    with _APPROVALS_LOCK:
        _APPROVALS = ApprovalService()
        return _APPROVALS
