"""
LangGraph StateGraph definition for the CONSORT deep-research agent.

Graph topology:

  plan_research → retrieve → evaluate ─┬─ sufficient → synthesize ─┬─ (more items) → plan_research
                                        ├─ need_more → retrieve     └─ (all done)  → generate_latex
                                        └─ need_web  → web_search → evaluate

The graph processes each CONSORT item iteratively, performing multi-hop
retrieval with a max of 3 hops per item before forcing synthesis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from langgraph.graph import END, StateGraph

from agent.state import AgentState, ConsortItem
from agent.nodes import (
    plan_research,
    retrieve,
    evaluate,
    web_search,
    synthesize,
    generate_latex,
)

logger = logging.getLogger(__name__)


# ── Conditional edge routers ────────────────────────────────────────────

def _route_after_evaluate(state: AgentState) -> str:
    """Route based on the evaluation verdict."""
    verdict = state.get("evaluation_result", "sufficient")
    if verdict == "need_more":
        return "retrieve"
    elif verdict == "need_web":
        return "web_search"
    else:
        return "synthesize"


def _route_after_synthesize(state: AgentState) -> str:
    """Route based on whether more CONSORT items remain."""
    idx = state["current_item_index"]
    total = len(state["consort_items"])
    if idx < total:
        return "plan_research"
    else:
        return "generate_latex"


# ── Graph construction ──────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construct and return the compiled LangGraph StateGraph.

    The graph is NOT compiled here so callers can inspect / modify
    before calling .compile().
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("plan_research", plan_research)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evaluate", evaluate)
    graph.add_node("web_search", web_search)
    graph.add_node("synthesize", synthesize)
    graph.add_node("generate_latex", generate_latex)

    # Set entry point
    graph.set_entry_point("plan_research")

    # Edges
    graph.add_edge("plan_research", "retrieve")
    graph.add_edge("retrieve", "evaluate")

    # Conditional: after evaluate
    graph.add_conditional_edges(
        "evaluate",
        _route_after_evaluate,
        {
            "retrieve": "retrieve",
            "web_search": "web_search",
            "synthesize": "synthesize",
        },
    )

    # web_search always loops back to evaluate
    graph.add_edge("web_search", "evaluate")

    # Conditional: after synthesize
    graph.add_conditional_edges(
        "synthesize",
        _route_after_synthesize,
        {
            "plan_research": "plan_research",
            "generate_latex": "generate_latex",
        },
    )

    # generate_latex → END
    graph.add_edge("generate_latex", END)

    return graph


def load_consort_items(consort_json_path: Path) -> list[ConsortItem]:
    """Load CONSORT checklist items from the JSON file."""
    with open(consort_json_path) as f:
        data = json.load(f)

    items: list[ConsortItem] = []
    for raw in data["items"]:
        items.append(
            ConsortItem(
                id=raw["id"],
                section=raw["section"],
                topic=raw["topic"],
                description=raw["description"],
                group=raw.get("group", ""),
            )
        )
    return items


def create_initial_state(consort_json_path: Path) -> AgentState:
    """Create the initial agent state from the CONSORT checklist."""
    items = load_consort_items(consort_json_path)
    return AgentState(
        consort_items=items,
        current_item_index=0,
        research_queries=[],
        retrieved_chunks=[],
        unfamiliar_terms=[],
        web_search_results={},
        evaluation_result="",
        hop_count=0,
        section_drafts={},
        latex_sections={},
        final_latex="",
    )
