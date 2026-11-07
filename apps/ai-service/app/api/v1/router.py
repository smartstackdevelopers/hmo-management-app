from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.approval.service import get_approval_service
from app.auth.deps import require_feature, require_service_auth
from app.context.trusted import TrustedCallerContext
from app.core.config import Settings, get_settings
from app.core.correlation import get_correlation_id, set_correlation_id
from app.core.errors import AiServiceError
from app.graph.foundation import ping_graph
from app.graph.runtime import execute_workflow, list_workflows
from app.prompts.schemas import PromptSummary
from app.prompts.store import get_prompt_store
from app.providers.factory import get_llm_provider
from app.api.v1.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    PromptListResponse,
    ProviderStatusResponse,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
)
from app import __version__

router = APIRouter()


@router.get("/health")
def v1_health() -> dict[str, str]:
    graph_status = ping_graph()
    return {
        "status": "ok",
        "service": "hmore-ai",
        "version": __version__,
        "graph": graph_status,
        "api": "v1",
    }


@router.get("/ready")
def v1_ready(settings: Settings = Depends(get_settings)) -> JSONResponse:
    """Readiness: process up, LangGraph compiles, auth secret present in non-test envs."""
    try:
        ping_graph()
    except Exception:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "graph_compile_failed"},
        )
    if settings.environment == "production" and not settings.service_auth_configured:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "ai_service_token_missing"},
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "service_auth_configured": settings.service_auth_configured,
            "llm_provider": settings.llm_provider,
        },
    )


@router.get("/workflows", dependencies=[Depends(require_feature("ai.workflow.execute"))])
def workflows_list() -> dict[str, list[str]]:
    return {"workflows": list_workflows()}


@router.post(
    "/workflows/execute",
    response_model=WorkflowExecuteResponse,
)
def workflows_execute(
    body: WorkflowExecuteRequest,
    ctx: TrustedCallerContext = Depends(require_feature("ai.workflow.execute")),
    settings: Settings = Depends(get_settings),
) -> WorkflowExecuteResponse:
    try:
        # Body organisation_id is never trusted as authorisation.
        if body.organisation_id is not None:
            ctx.ensure_org(body.organisation_id)
        result = execute_workflow(
            workflow_id=body.workflow_id,
            ctx=ctx,
            settings=settings,
            message=body.message,
            require_human_gate=body.require_human_gate,
            input_payload=body.model_dump(),
        )
        return WorkflowExecuteResponse(**result)
    except AiServiceError as exc:
        raise exc.to_http() from exc


@router.get("/prompts", response_model=PromptListResponse)
def prompts_list(
    ctx: TrustedCallerContext = Depends(require_feature("ai.prompts.read")),
) -> PromptListResponse:
    _ = ctx
    store = get_prompt_store()
    items = [
        PromptSummary(
            prompt_id=v.prompt_id,
            version=v.version,
            status=v.status,
            workflow_or_feature=v.workflow_or_feature,
            created_at=v.created_at,
            published_at=v.published_at,
        ).model_dump(mode="json")
        for v in store.list_versions()
    ]
    # Summaries only — full templates are not exposed via the gateway.
    return PromptListResponse(items=items)


@router.get("/provider", response_model=ProviderStatusResponse)
def provider_status(
    ctx: TrustedCallerContext = Depends(require_service_auth),
    settings: Settings = Depends(get_settings),
) -> ProviderStatusResponse:
    _ = ctx
    try:
        provider = get_llm_provider(settings)
    except AiServiceError as exc:
        return ProviderStatusResponse(
            configured_provider=settings.llm_provider,
            available=False,
            detail=exc.message,
        )
    if provider is None:
        return ProviderStatusResponse(
            configured_provider="none",
            available=False,
            detail="No LLM provider configured (LLM_PROVIDER=none)",
        )
    return ProviderStatusResponse(
        configured_provider=provider.name,
        available=provider.is_available(),
        detail="Provider interface ready" if provider.is_available() else "Provider unavailable",
    )


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalDecisionResponse)
def approval_decide(
    approval_id: str,
    body: ApprovalDecisionRequest,
    ctx: TrustedCallerContext = Depends(require_feature("ai.approvals")),
) -> ApprovalDecisionResponse:
    try:
        record = get_approval_service().decide(
            approval_id=approval_id,
            ctx=ctx,
            approve=body.approve,
            note=body.note,
        )
        return ApprovalDecisionResponse(
            approval_id=record.approval_id,
            status=record.status.value,
            reviewer_user_id=str(record.reviewer_user_id) if record.reviewer_user_id else None,
            is_human_approved=record.is_human_approved,
            proposed_action_source=record.proposed_action.source,
        )
    except AiServiceError as exc:
        raise exc.to_http() from exc


@router.get("/approvals/{approval_id}", response_model=ApprovalDecisionResponse)
def approval_get(
    approval_id: str,
    ctx: TrustedCallerContext = Depends(require_feature("ai.approvals")),
) -> ApprovalDecisionResponse:
    try:
        record = get_approval_service().get(approval_id, ctx)
        return ApprovalDecisionResponse(
            approval_id=record.approval_id,
            status=record.status.value,
            reviewer_user_id=str(record.reviewer_user_id) if record.reviewer_user_id else None,
            is_human_approved=record.is_human_approved,
            proposed_action_source=record.proposed_action.source,
        )
    except AiServiceError as exc:
        raise exc.to_http() from exc
