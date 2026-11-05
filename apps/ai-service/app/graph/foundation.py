from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class FoundationState(TypedDict):
    ping: str


def _echo(state: FoundationState) -> FoundationState:
    return {"ping": state.get("ping", "ok")}


def build_foundation_graph():
    graph = StateGraph(FoundationState)
    graph.add_node("echo", _echo)
    graph.add_edge(START, "echo")
    graph.add_edge("echo", END)
    return graph.compile()


def ping_graph() -> str:
    compiled = build_foundation_graph()
    result = compiled.invoke({"ping": "ok"})
    return result["ping"]
