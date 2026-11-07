from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from app.approval.service import get_approval_service
from app.context.trusted import TrustedCallerContext
from app.core.config import Settings
from app.core.correlation import get_correlation_id
from app.core.errors import WorkflowError
from app.graph.echo_workflow import build_foundation_echo_graph
from app.graph.foundation import ping_graph
from app.prompts.store import get_prompt_store
from app.tools.registry import build_default_tool_registry
from app.usage.metadata import UsageMetadata

SUPPORTED_WORKFLOWS = frozenset({"foundation_ping", "foundation_echo"})


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
) -> dict[str, Any]:
    if workflow_id not in SUPPORTED_WORKFLOWS:
        raise WorkflowError(f"Unsupported workflow '{workflow_id}'", status_code=404)

    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    usage = UsageMetadata(
        request_id=request_id,
        correlation_id=get_correlation_id(),
        workflow_id=workflow_id,
        organisation_id=ctx.organisation_id,
        user_id=ctx.user_id,
        status="started",
    )

    def _run() -> dict[str, Any]:
        if workflow_id == "foundation_ping":
            ping = ping_graph()
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": {"ping": ping},
                "requires_approval": False,
                "approval_id": None,
            }

        # foundation_echo — body org fields ignored; trusted ctx only
        if input_payload and "organisation_id" in input_payload:
            # Explicitly ignore / reject impersonation attempts via body
            claimed = input_payload.get("organisation_id")
            if claimed and str(claimed) != str(ctx.organisation_id):
                raise WorkflowError("organisation_id in body is not trusted", status_code=403)

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
                # Do not return full rendered prompt with PII amplification in API by default
            },
            "requires_approval": bool(final.get("requires_approval")),
            "approval_id": final.get("approval_id"),
            "proposed_action_summary": final.get("proposed_action_summary"),
        }

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            outcome = future.result(timeout=settings.workflow_timeout_seconds)
        usage.status = outcome.get("status", "completed")
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        outcome["request_id"] = request_id
        outcome["usage"] = usage.to_public_dict()
        outcome["organisation_id"] = str(ctx.organisation_id)
        return outcome
    except FuturesTimeout as exc:
        usage.status = "timeout"
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        raise WorkflowError("Workflow execution timed out", status_code=504) from exc
    except WorkflowError:
        raise
    except Exception as exc:  # noqa: BLE001
        usage.status = "failed"
        usage.duration_ms = int((time.perf_counter() - started) * 1000)
        raise WorkflowError("Workflow execution failed", status_code=500) from exc
