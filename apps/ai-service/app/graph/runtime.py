from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from app.approval.service import get_approval_service
from app.budget.client import BudgetExceededError, reconcile_usage, reserve_budget
from app.budget.features import feature_for_workflow
from app.context.trusted import TrustedCallerContext
from app.core.config import Settings
from app.core.correlation import get_correlation_id
from app.core.errors import WorkflowError
from app.graph.echo_workflow import build_foundation_echo_graph
from app.graph.foundation import ping_graph
from app.prompts.store import get_prompt_store
from app.tools.registry import build_default_tool_registry
from app.usage.metadata import UsageMetadata

SUPPORTED_WORKFLOWS = frozenset(
    {
        "foundation_ping",
        "foundation_echo",
        "foundation_routed_echo",
        "notes_analysis",
        "case_summary",
        "document_check",
        "support_plan_draft",
        "housing_application_analysis",
        "compliance_explanation",
        "tenant_assistant",
        "operational_search",
    }
)

# foundation_ping is infrastructure-only and non-billable.
NON_BILLABLE_WORKFLOWS = frozenset({"foundation_ping"})


def list_workflows() -> list[str]:
    return sorted(SUPPORTED_WORKFLOWS)


def execute_workflow(
    *,
    workflow_id: str,
    ctx: TrustedCallerContext,
    settings: Settings,
    message: str = "",
    require_human_gate: bool = False,
    input_payload: dict[str, Any] | None = None,
    batch_job_id: str | None = None,
) -> dict[str, Any]:
    if workflow_id not in SUPPORTED_WORKFLOWS:
        raise WorkflowError(f"Unsupported workflow '{workflow_id}'", status_code=404)

    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    feature_id = feature_for_workflow(workflow_id)
    billable = workflow_id not in NON_BILLABLE_WORKFLOWS
    usage = UsageMetadata(
        request_id=request_id,
        correlation_id=get_correlation_id(),
        workflow_id=workflow_id,
        organisation_id=ctx.organisation_id,
        user_id=ctx.user_id,
        status="started",
        batch_job_id=batch_job_id,
    )

    def _reject_body_org() -> None:
        if input_payload and input_payload.get("organisation_id"):
            claimed = input_payload.get("organisation_id")
            if claimed and str(claimed) != str(ctx.organisation_id):
                raise WorkflowError("organisation_id in body is not trusted", status_code=403)

    def _run_routed() -> dict[str, Any]:
        from app.prompts.seed import FOUNDATION_PROMPT_ID
        from app.routing.executor import run_routed_completion

        _reject_body_org()
        store = get_prompt_store()
        record, rendered = store.render(
            FOUNDATION_PROMPT_ID,
            variables={
                "organisation_id": str(ctx.organisation_id),
                "role": ctx.role,
                "message": message,
            },
        )
        quality = input_payload.get("quality_requirement") if input_payload else None
        routed = run_routed_completion(
            settings=settings,
            organisation_id=ctx.organisation_id,
            workflow_id=workflow_id,
            prompt_id=record.prompt_id,
            prompt_version=record.version,
            rendered_prompt=rendered,
            user_message=message,
            quality_requirement=quality,
            cache_eligible=True,
        )
        usage.prompt_id = record.prompt_id
        usage.prompt_version = record.version
        usage.provider = routed.get("provider")
        usage.model = routed.get("model_id")
        usage.prompt_tokens = routed.get("prompt_tokens")
        usage.completion_tokens = routed.get("completion_tokens")
        usage.total_tokens = routed.get("total_tokens")
        usage.cache_hit = routed.get("cache_status") == "hit"
        esc = routed.get("escalation")
        usage.escalation_occurred = bool(esc)
        usage.escalation_reason = (esc or {}).get("reason") if esc else None
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "result": {
                "content": routed.get("content"),
                "prompt_id": record.prompt_id,
                "prompt_version": record.version,
                "routing": routed.get("routing"),
                "escalation": routed.get("escalation"),
                "cache_status": routed.get("cache_status"),
            },
            "requires_approval": False,
            "approval_id": None,
            "provider_request_id": routed.get("provider_request_id"),
        }

    def _run() -> dict[str, Any]:
        if workflow_id == "foundation_ping":
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": {"ping": ping_graph()},
                "requires_approval": False,
                "approval_id": None,
            }

        if workflow_id == "foundation_routed_echo":
            return _run_routed()

        if workflow_id == "notes_analysis":
            from app.graph.notes_analysis import run_notes_analysis

            _reject_body_org()
            note_payload = (input_payload or {}).get("note") or {}
            if not isinstance(note_payload, dict) or not note_payload:
                raise WorkflowError("notes_analysis requires input_payload.note", status_code=422)
            analysed = run_notes_analysis(
                settings=settings,
                organisation_id=ctx.organisation_id,
                note_payload=note_payload,
            )
            usage.prompt_id = analysed.get("prompt_id")
            usage.prompt_version = analysed.get("prompt_version")
            usage.provider = analysed.get("provider")
            usage.model = analysed.get("model_id")
            usage.prompt_tokens = analysed.get("prompt_tokens")
            usage.completion_tokens = analysed.get("completion_tokens")
            usage.total_tokens = analysed.get("total_tokens")
            usage.cache_hit = analysed.get("cache_status") == "hit"
            esc = analysed.get("escalation")
            usage.escalation_occurred = bool(esc)
            usage.escalation_reason = (esc or {}).get("reason") if esc else None
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": analysed,
                "requires_approval": True,
                "approval_id": None,
                "provider_request_id": analysed.get("provider_request_id"),
            }

        if workflow_id == "case_summary":
            from app.graph.case_summary import run_case_summary

            _reject_body_org()
            packet = (input_payload or {}).get("packet") or {}
            if not isinstance(packet, dict) or not isinstance(packet.get("profile"), dict):
                raise WorkflowError("case_summary requires input_payload.packet", status_code=422)
            summarised = run_case_summary(
                settings=settings,
                organisation_id=ctx.organisation_id,
                packet=packet,
            )
            usage.prompt_id = summarised.get("prompt_id")
            usage.prompt_version = summarised.get("prompt_version")
            usage.provider = summarised.get("provider")
            usage.model = summarised.get("model_id")
            usage.prompt_tokens = summarised.get("prompt_tokens")
            usage.completion_tokens = summarised.get("completion_tokens")
            usage.total_tokens = summarised.get("total_tokens")
            usage.cache_hit = summarised.get("cache_status") == "hit"
            esc = summarised.get("escalation")
            usage.escalation_occurred = bool(esc)
            usage.escalation_reason = (esc or {}).get("reason") if esc else None
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": summarised,
                "requires_approval": True,
                "approval_id": None,
                "provider_request_id": summarised.get("provider_request_id"),
            }

        if workflow_id == "document_check":
            from app.graph.document_check import run_document_check

            _reject_body_org()
            findings = (input_payload or {}).get("findings") or []
            if not isinstance(findings, list):
                raise WorkflowError("document_check requires input_payload.findings", status_code=422)
            analysed = run_document_check(
                settings=settings,
                organisation_id=ctx.organisation_id,
                findings=findings,
                excerpt=str((input_payload or {}).get("excerpt") or ""),
            )
            usage.prompt_id = analysed.get("prompt_id")
            usage.prompt_version = analysed.get("prompt_version")
            usage.provider = analysed.get("provider")
            usage.model = analysed.get("model_id")
            usage.prompt_tokens = analysed.get("prompt_tokens")
            usage.completion_tokens = analysed.get("completion_tokens")
            usage.total_tokens = analysed.get("total_tokens")
            usage.cache_hit = analysed.get("cache_status") == "hit"
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": analysed,
                "requires_approval": True,
                "approval_id": None,
                "provider_request_id": analysed.get("provider_request_id"),
            }

        if workflow_id == "support_plan_draft":
            from app.graph.support_plan_draft import run_support_plan_draft

            _reject_body_org()
            packet = (input_payload or {}).get("packet")
            if not isinstance(packet, dict):
                raise WorkflowError("support_plan_draft requires input_payload.packet", status_code=422)
            drafted = run_support_plan_draft(
                settings=settings,
                organisation_id=ctx.organisation_id,
                packet=packet,
            )
            usage.prompt_id = drafted.get("prompt_id")
            usage.prompt_version = drafted.get("prompt_version")
            usage.provider = drafted.get("provider")
            usage.model = drafted.get("model_id")
            usage.prompt_tokens = drafted.get("prompt_tokens")
            usage.completion_tokens = drafted.get("completion_tokens")
            usage.total_tokens = drafted.get("total_tokens")
            usage.cache_hit = drafted.get("cache_status") == "hit"
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": drafted,
                "requires_approval": True,
                "approval_id": None,
                "provider_request_id": drafted.get("provider_request_id"),
            }

        if workflow_id == "housing_application_analysis":
            from app.graph.housing_application_analysis import run_housing_application_analysis

            _reject_body_org()
            findings = (input_payload or {}).get("findings") or []
            if not isinstance(findings, list):
                raise WorkflowError(
                    "housing_application_analysis requires input_payload.findings", status_code=422
                )
            analysed = run_housing_application_analysis(
                settings=settings,
                organisation_id=ctx.organisation_id,
                findings=findings,
                application_reference=str((input_payload or {}).get("application_reference") or "unknown"),
            )
            usage.prompt_id = analysed.get("prompt_id")
            usage.prompt_version = analysed.get("prompt_version")
            usage.provider = analysed.get("provider")
            usage.model = analysed.get("model_id")
            usage.prompt_tokens = analysed.get("prompt_tokens")
            usage.completion_tokens = analysed.get("completion_tokens")
            usage.total_tokens = analysed.get("total_tokens")
            usage.cache_hit = analysed.get("cache_status") == "hit"
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": analysed,
                "requires_approval": True,
                "approval_id": None,
                "provider_request_id": analysed.get("provider_request_id"),
            }

        if workflow_id == "compliance_explanation":
            from app.graph.compliance_explanation import run_compliance_explanation

            _reject_body_org()
            findings = (input_payload or {}).get("findings") or []
            if not isinstance(findings, list):
                raise WorkflowError(
                    "compliance_explanation requires input_payload.findings", status_code=422
                )
            explained = run_compliance_explanation(
                settings=settings,
                organisation_id=ctx.organisation_id,
                findings=findings,
            )
            usage.prompt_id = explained.get("prompt_id")
            usage.prompt_version = explained.get("prompt_version")
            usage.provider = explained.get("provider")
            usage.model = explained.get("model_id")
            usage.prompt_tokens = explained.get("prompt_tokens")
            usage.completion_tokens = explained.get("completion_tokens")
            usage.total_tokens = explained.get("total_tokens")
            usage.cache_hit = explained.get("cache_status") == "hit"
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": explained,
                "requires_approval": True,
                "approval_id": None,
                "provider_request_id": explained.get("provider_request_id"),
            }

        if workflow_id == "operational_search":
            from app.graph.operational_search import run_operational_search

            _reject_body_org()
            question = str((input_payload or {}).get("question") or "")
            interpreted = run_operational_search(question=question)
            usage.prompt_id = interpreted.get("prompt_id")
            usage.prompt_version = interpreted.get("prompt_version")
            usage.provider = interpreted.get("provider")
            usage.model = interpreted.get("model_id")
            usage.prompt_tokens = 0
            usage.completion_tokens = 0
            usage.total_tokens = 0
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": interpreted,
                "requires_approval": False,
                "approval_id": None,
                "provider_request_id": None,
            }

        if workflow_id == "tenant_assistant":
            from app.graph.tenant_assistant import run_tenant_assistant

            _reject_body_org()
            snippets = (input_payload or {}).get("approved_snippets") or []
            if not isinstance(snippets, list):
                raise WorkflowError(
                    "tenant_assistant requires input_payload.approved_snippets", status_code=422
                )
            answered = run_tenant_assistant(
                settings=settings,
                organisation_id=ctx.organisation_id,
                question=str((input_payload or {}).get("question") or ""),
                approved_snippets=snippets,
            )
            usage.prompt_id = answered.get("prompt_id")
            usage.prompt_version = answered.get("prompt_version")
            usage.provider = answered.get("provider")
            usage.model = answered.get("model_id")
            usage.prompt_tokens = answered.get("prompt_tokens")
            usage.completion_tokens = answered.get("completion_tokens")
            usage.total_tokens = answered.get("total_tokens")
            usage.cache_hit = answered.get("cache_status") == "hit"
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": answered,
                "requires_approval": False,
                "approval_id": None,
                "provider_request_id": answered.get("provider_request_id"),
            }

        _reject_body_org()
        store = get_prompt_store()
        tools = build_default_tool_registry()
        approvals = get_approval_service()
        graph = build_foundation_echo_graph(
            store=store,
            tools=tools,
            approvals=approvals,
            ctx=ctx,
            require_human_gate=require_human_gate,
        )
        final = graph.invoke(
            {
                "organisation_id": str(ctx.organisation_id),
                "user_id": str(ctx.user_id),
                "role": ctx.role,
                "correlation_id": get_correlation_id(),
                "message": message,
                "status": "started",
            }
        )
        usage.prompt_id = final.get("prompt_id")
        usage.prompt_version = final.get("prompt_version")
        return {
            "workflow_id": workflow_id,
            "status": final.get("status", "completed"),
            "result": {
                "tool_output": final.get("tool_output"),
                "prompt_id": final.get("prompt_id"),
                "prompt_version": final.get("prompt_version"),
            },
            "requires_approval": bool(final.get("requires_approval")),
            "approval_id": final.get("approval_id"),
            "proposed_action_summary": final.get("proposed_action_summary"),
        }

    def _reconcile(execution_status: str, extra: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {
            "request_id": request_id,
            "organisation_id": str(ctx.organisation_id),
            "execution_status": execution_status,
            "feature_id": feature_id,
            "workflow_id": workflow_id,
            "user_id": str(ctx.user_id),
            "provider": usage.provider,
            "model_id": usage.model,
            "prompt_id": usage.prompt_id,
            "prompt_version": usage.prompt_version,
            "batch_job_id": batch_job_id,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cache_hit": usage.cache_hit,
            "escalation_occurred": usage.escalation_occurred,
            "escalation_reason": usage.escalation_reason,
            "duration_ms": usage.duration_ms,
            "metadata": {"correlation_id": usage.correlation_id},
        }
        if extra:
            payload.update(extra)
        reconcile_usage(settings, payload=payload)

    # Hard cap enforcement before billable dispatch.
    try:
        reserve_budget(
            settings,
            request_id=request_id,
            organisation_id=ctx.organisation_id,
            user_id=ctx.user_id,
            feature_id=feature_id,
            workflow_id=workflow_id,
            billable=billable,
            cache_hit=False,
        )
    except BudgetExceededError as exc:
        usage.status = "rejected_budget"
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        raise

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            outcome = future.result(timeout=settings.workflow_timeout_seconds)
        usage.status = outcome.get("status", "completed")
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        outcome["request_id"] = request_id
        outcome["usage"] = usage.to_public_dict()
        outcome["organisation_id"] = str(ctx.organisation_id)
        _reconcile(
            "completed" if usage.status == "completed" else "failed",
            {"provider_request_id": outcome.get("provider_request_id")},
        )
        return outcome
    except FuturesTimeout as exc:
        usage.status = "timeout"
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        _reconcile("failed", {"metadata": {"reason": "timeout"}})
        raise WorkflowError("Workflow execution timed out", status_code=504) from exc
    except WorkflowError:
        usage.status = "failed"
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        _reconcile("failed")
        raise
    except Exception as exc:  # noqa: BLE001
        usage.status = "failed"
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        _reconcile("failed")
        raise WorkflowError("Workflow execution failed", status_code=500) from exc
