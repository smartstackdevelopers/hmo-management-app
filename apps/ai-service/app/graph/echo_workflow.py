from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.approval.service import ApprovalService
from app.context.trusted import TrustedCallerContext
from app.graph.state import BaseWorkflowState
from app.prompts.seed import FOUNDATION_PROMPT_ID
from app.prompts.store import PromptStore
from app.tools.registry import ToolRegistry


def build_foundation_echo_graph(
    *,
    store: PromptStore,
    tools: ToolRegistry,
    approvals: ApprovalService,
    ctx: TrustedCallerContext,
    require_human_gate: bool,
):
    """Controlled F3.1 sample workflow — not a product agent.

    Path: resolve_prompt → approved_tool → optional approval pause → end
    """

    def resolve_prompt(state: BaseWorkflowState) -> BaseWorkflowState:
        record, rendered = store.render(
            FOUNDATION_PROMPT_ID,
            variables={
                "organisation_id": str(ctx.organisation_id),
                "role": ctx.role,
                "message": state.get("message", ""),
            },
        )
        return {
            **state,
            "prompt_id": record.prompt_id,
            "prompt_version": record.version,
            "rendered_prompt": rendered,
            "status": "prompt_resolved",
        }

    def run_tool(state: BaseWorkflowState) -> BaseWorkflowState:
        output = tools.invoke("echo_safe", message=state.get("message", ""))
        return {**state, "tool_output": output, "status": "tool_complete"}

    def maybe_pause(state: BaseWorkflowState) -> BaseWorkflowState:
        if not require_human_gate:
            return {**state, "requires_approval": False, "status": "completed"}
        record = approvals.create_pending(
            ctx=ctx,
            action_type="foundation.echo.apply",
            summary=f"Apply echo output: {state.get('tool_output', '')[:200]}",
            payload={"tool_output": state.get("tool_output")},
            workflow_id="foundation_echo",
        )
        return {
            **state,
            "requires_approval": True,
            "approval_id": record.approval_id,
            "proposed_action_summary": record.proposed_action.summary,
            "status": "awaiting_human_approval",
        }

    def route_after_tool(state: BaseWorkflowState) -> str:
        return "pause" if require_human_gate else "done"

    graph = StateGraph(BaseWorkflowState)
    graph.add_node("resolve_prompt", resolve_prompt)
    graph.add_node("run_tool", run_tool)
    graph.add_node("maybe_pause", maybe_pause)
    graph.add_edge(START, "resolve_prompt")
    graph.add_edge("resolve_prompt", "run_tool")
    graph.add_conditional_edges(
        "run_tool",
        route_after_tool,
        {"pause": "maybe_pause", "done": END},
    )
    graph.add_edge("maybe_pause", END)
    return graph.compile()
