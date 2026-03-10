from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, START, END

from app.agents.reasoning_agent import reasoning_agent


class MatchingState(TypedDict, total=False):
    query: str
    tender_requirements: Dict[str, Any]
    matches: List[Dict[str, Any]]
    reasoning_summary: str


def build_matching_graph():
    graph_builder = StateGraph(MatchingState)

    graph_builder.add_node("reasoning_agent", reasoning_agent)

    graph_builder.add_edge(START, "reasoning_agent")
    graph_builder.add_edge("reasoning_agent", END)

    return graph_builder.compile()