"""
LangGraph agent state definition.

The state flows through every node in the graph and accumulates research
results, section drafts, and the final LaTeX output.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ConsortItem(TypedDict):
    """A single CONSORT checklist item."""

    id: str
    section: str
    topic: str
    description: str
    group: str  # e.g. "Randomisation", empty string if none


class RetrievedChunkDict(TypedDict):
    """Serialisable representation of a retrieved chunk."""

    text: str
    score: float
    source_file: str
    page_number: int


class AgentState(TypedDict):
    """
    Full state that flows through the LangGraph deep-research graph.

    Fields are accumulated across nodes; LangGraph merges dicts automatically
    when a node returns a partial update.
    """

    # ── CONSORT items to fulfil ─────────────────────────────────────────
    consort_items: list[ConsortItem]
    current_item_index: int

    # ── Research planning ───────────────────────────────────────────────
    research_queries: list[str]          # queries for the current item

    # ── Retrieval results ───────────────────────────────────────────────
    retrieved_chunks: list[RetrievedChunkDict]

    # ── Web search hydration ────────────────────────────────────────────
    unfamiliar_terms: list[str]
    web_search_results: dict[str, str]   # term -> definition

    # ── Evaluation ──────────────────────────────────────────────────────
    evaluation_result: str               # "sufficient" | "need_more" | "need_web"
    hop_count: int                       # multi-hop counter (max 3)

    # ── Synthesis ───────────────────────────────────────────────────────
    section_drafts: dict[str, str]       # consort item id -> prose draft

    # ── LaTeX output ────────────────────────────────────────────────────
    latex_sections: dict[str, str]       # consort item id -> LaTeX fragment
    final_latex: str                     # complete .tex document
