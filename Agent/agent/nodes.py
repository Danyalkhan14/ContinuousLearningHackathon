"""
LangGraph node functions for the CONSORT deep-research agent.

Every node is a pure function:  State → partial State update.

Uses the OpenAI Chat Completions API with GPT-5.2:
  POST /v1/chat/completions
  - messages[]: role is "developer" (not "system"), "user", "assistant"
  - model: "gpt-5.2"
  - max_completion_tokens  (not the deprecated max_tokens)
  - reasoning_effort: none | minimal | low | medium | high | xhigh

API reference: https://platform.openai.com/docs/api-reference/chat/create
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from agent.state import AgentState
from config import Settings, get_settings
from retrieval.client import QdrantRetriever
from search.you_client import YouSearchClient
from latex.generator import sections_to_latex

logger = logging.getLogger(__name__)

# ── Shared singletons (initialised lazily) ──────────────────────────────

_settings: Settings | None = None
_openai: OpenAI | None = None
_retriever: QdrantRetriever | None = None
_you_client: YouSearchClient | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=_get_settings().openai_api_key)
    return _openai


def _get_retriever() -> QdrantRetriever:
    global _retriever
    if _retriever is None:
        _retriever = QdrantRetriever(_get_settings())
    return _retriever


def _get_you_client() -> YouSearchClient:
    global _you_client
    if _you_client is None:
        _you_client = YouSearchClient(_get_settings())
    return _you_client


def _chat(
    messages: list[dict[str, str]],
    *,
    max_completion_tokens: int | None = None,
    reasoning_effort: str | None = None,
    response_format: dict | None = None,
) -> str:
    """
    Call OpenAI Chat Completions with GPT-5.2.

    Uses the documented API parameters:
      https://platform.openai.com/docs/api-reference/chat/create

    Messages use "developer" role for system-level instructions
    (not the legacy "system" role).
    """
    settings = _get_settings()
    client = _get_openai()

    kwargs: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "max_completion_tokens": max_completion_tokens or settings.llm_max_completion_tokens,
        "reasoning_effort": reasoning_effort or settings.llm_reasoning_effort,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    completion = client.chat.completions.create(**kwargs)
    content = completion.choices[0].message.content or ""
    return content.strip()


# ═══════════════════════════════════════════════════════════════════════
# NODE 1: plan_research
# ═══════════════════════════════════════════════════════════════════════

def plan_research(state: AgentState) -> dict[str, Any]:
    """
    Decompose the current CONSORT item into 2-5 targeted retrieval queries.

    The LLM generates queries that will be run against the Qdrant vector
    store to gather evidence for this specific checklist item.
    """
    idx = state["current_item_index"]
    item = state["consort_items"][idx]

    prompt = (
        f"You are a clinical research analyst. Given the following CONSORT 2025 "
        f"checklist item, generate 2-5 specific search queries to retrieve relevant "
        f"evidence from a corpus of clinical trial documents (protocols, SAPs, "
        f"summary tables, ClinicalTrials.gov records).\n\n"
        f"CONSORT Item ID: {item['id']}\n"
        f"Section: {item['section']}\n"
        f"Topic: {item['topic']}\n"
        f"Description: {item['description']}\n\n"
        f"Return ONLY a JSON array of query strings. Example:\n"
        f'["query one", "query two", "query three"]'
    )

    messages = [
        {"role": "developer", "content": "You are a clinical trial report writing assistant."},
        {"role": "user", "content": prompt},
    ]

    raw = _chat(
        messages,
        max_completion_tokens=1024,
        reasoning_effort="low",
    )

    # Parse the JSON array of queries
    try:
        queries = json.loads(raw)
        if not isinstance(queries, list):
            queries = [raw]
    except json.JSONDecodeError:
        logger.warning("Failed to parse queries JSON, using raw text as single query")
        queries = [raw]

    logger.info(
        "Plan research for item %s (%s): %d queries",
        item["id"],
        item["topic"],
        len(queries),
    )

    return {
        "research_queries": queries,
        "retrieved_chunks": [],
        "hop_count": 0,
        "evaluation_result": "",
        "unfamiliar_terms": [],
        "web_search_results": state.get("web_search_results", {}),
    }


# ═══════════════════════════════════════════════════════════════════════
# NODE 2: retrieve
# ═══════════════════════════════════════════════════════════════════════

def retrieve(state: AgentState) -> dict[str, Any]:
    """
    Execute the research queries against Qdrant and accumulate results.

    Uses multi_query_search for de-duplication across queries.
    """
    retriever = _get_retriever()
    queries = state["research_queries"]

    chunks = retriever.multi_query_search(queries, top_k_per_query=5)

    # Convert to serialisable dicts
    chunk_dicts = [
        {
            "text": c.text,
            "score": c.score,
            "source_file": c.source_file,
            "page_number": c.page_number,
        }
        for c in chunks
    ]

    # Merge with any existing chunks from previous hops
    existing = state.get("retrieved_chunks", [])
    seen = {c["text"] for c in existing}
    for cd in chunk_dicts:
        if cd["text"] not in seen:
            existing.append(cd)
            seen.add(cd["text"])

    return {
        "retrieved_chunks": existing,
        "hop_count": state.get("hop_count", 0) + 1,
    }


# ═══════════════════════════════════════════════════════════════════════
# NODE 3: evaluate
# ═══════════════════════════════════════════════════════════════════════

def evaluate(state: AgentState) -> dict[str, Any]:
    """
    Assess whether the retrieved evidence is sufficient for the current
    CONSORT item, or if we need more retrieval / web search.

    Returns one of:
      - "sufficient"  → proceed to synthesis
      - "need_more"   → another retrieval hop (if hop_count < 3)
      - "need_web"    → hydrate unfamiliar terms via You.com
    """
    idx = state["current_item_index"]
    item = state["consort_items"][idx]
    chunks = state["retrieved_chunks"]
    hop_count = state.get("hop_count", 0)

    # Build a summary of evidence
    evidence_summary = "\n\n".join(
        f"[{c['source_file']} p.{c['page_number']}] {c['text'][:500]}"
        for c in chunks[:15]  # cap to avoid token overflow
    )

    prompt = (
        f"You are evaluating whether the following retrieved evidence is "
        f"sufficient to write the CONSORT report section below.\n\n"
        f"CONSORT Item ID: {item['id']}\n"
        f"Section: {item['section']}\n"
        f"Topic: {item['topic']}\n"
        f"Description: {item['description']}\n\n"
        f"--- RETRIEVED EVIDENCE ---\n{evidence_summary}\n"
        f"--- END EVIDENCE ---\n\n"
        f"Respond with a JSON object with exactly two keys:\n"
        f'  "verdict": one of "sufficient", "need_more", or "need_web"\n'
        f'  "details": a brief explanation\n'
        f'  "unfamiliar_terms": list of any clinical/statistical terms in the '
        f"evidence that need definition (empty list if none)\n"
        f'  "follow_up_queries": if verdict is "need_more", list 1-3 follow-up '
        f"queries to refine the search (empty list otherwise)\n"
    )

    messages = [
        {"role": "developer", "content": "You are a clinical trial evidence evaluator."},
        {"role": "user", "content": prompt},
    ]

    raw = _chat(messages, max_completion_tokens=2048, reasoning_effort="low")

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse evaluation JSON; defaulting to sufficient")
        result = {"verdict": "sufficient", "details": raw, "unfamiliar_terms": [], "follow_up_queries": []}

    verdict = result.get("verdict", "sufficient")

    # Force "sufficient" if we've exhausted hops
    if verdict == "need_more" and hop_count >= 3:
        logger.info("Max hops reached (%d); forcing sufficient", hop_count)
        verdict = "sufficient"

    # If follow-up queries are provided, update research_queries for next hop
    follow_ups = result.get("follow_up_queries", [])
    unfamiliar = result.get("unfamiliar_terms", [])

    logger.info(
        "Evaluate item %s: verdict=%s, unfamiliar=%d terms, follow_ups=%d",
        item["id"],
        verdict,
        len(unfamiliar),
        len(follow_ups),
    )

    update: dict[str, Any] = {
        "evaluation_result": verdict,
        "unfamiliar_terms": unfamiliar,
    }
    if follow_ups:
        update["research_queries"] = follow_ups

    return update


# ═══════════════════════════════════════════════════════════════════════
# NODE 4: web_search
# ═══════════════════════════════════════════════════════════════════════

def web_search(state: AgentState) -> dict[str, Any]:
    """
    Hydrate unfamiliar terms via You.com web search.

    Merges new definitions into the existing web_search_results dict.
    """
    you = _get_you_client()
    terms = state.get("unfamiliar_terms", [])

    if not terms:
        return {"web_search_results": state.get("web_search_results", {})}

    new_defs = you.hydrate_terms(terms)

    merged = {**state.get("web_search_results", {}), **new_defs}
    logger.info("Web search hydrated %d terms (total: %d)", len(new_defs), len(merged))

    return {
        "web_search_results": merged,
        # After hydration, re-evaluate
        "evaluation_result": "sufficient",
    }


# ═══════════════════════════════════════════════════════════════════════
# NODE 5: synthesize
# ═══════════════════════════════════════════════════════════════════════

def synthesize(state: AgentState) -> dict[str, Any]:
    """
    Synthesize retrieved evidence + web definitions into a prose draft
    for the current CONSORT section.
    """
    idx = state["current_item_index"]
    item = state["consort_items"][idx]
    chunks = state["retrieved_chunks"]
    web_defs = state.get("web_search_results", {})

    # Build context
    evidence = "\n\n".join(
        f"[Source: {c['source_file']}, p.{c['page_number']}]\n{c['text']}"
        for c in chunks[:20]
    )

    definitions_text = ""
    if web_defs:
        definitions_text = "\n\n--- TERM DEFINITIONS ---\n"
        definitions_text += "\n".join(f"- {term}: {defn}" for term, defn in web_defs.items())

    prompt = (
        f"You are writing a section of a CONSORT 2025-compliant clinical trial "
        f"report. Using ONLY the evidence below, write the section described.\n\n"
        f"CONSORT Item: {item['id']} – {item['topic']}\n"
        f"Required content: {item['description']}\n"
        f"Section: {item['section']}\n\n"
        f"--- EVIDENCE FROM TRIAL DOCUMENTS ---\n{evidence}\n"
        f"--- END EVIDENCE ---\n"
        f"{definitions_text}\n\n"
        f"Instructions:\n"
        f"- Write in formal scientific prose suitable for a journal submission.\n"
        f"- Be specific: include numbers, dates, statistical details when available.\n"
        f"- If information is not available in the evidence, state that explicitly.\n"
        f"- Do NOT invent data. Only report what is supported by the evidence.\n"
        f"- Use past tense for completed actions.\n"
    )

    messages = [
        {"role": "developer", "content": "You are an expert clinical trial report writer."},
        {"role": "user", "content": prompt},
    ]

    draft = _chat(messages, max_completion_tokens=4096, reasoning_effort="medium")

    # Store the draft
    drafts = {**state.get("section_drafts", {})}
    drafts[item["id"]] = draft

    # Advance to next item
    next_idx = idx + 1

    logger.info(
        "Synthesized item %s (%s): %d chars",
        item["id"],
        item["topic"],
        len(draft),
    )

    return {
        "section_drafts": drafts,
        "current_item_index": next_idx,
    }


# ═══════════════════════════════════════════════════════════════════════
# NODE 6: generate_latex
# ═══════════════════════════════════════════════════════════════════════

def generate_latex(state: AgentState) -> dict[str, Any]:
    """
    Convert all section drafts into a complete LaTeX document.

    Delegates to latex.generator for the actual template assembly.
    """
    drafts = state.get("section_drafts", {})
    consort_items = state["consort_items"]

    # Generate LaTeX for each section via the LLM
    latex_sections: dict[str, str] = {}
    for item in consort_items:
        item_id = item["id"]
        draft = drafts.get(item_id, "")
        if not draft:
            latex_sections[item_id] = f"% No evidence found for CONSORT item {item_id}\n"
            continue

        messages = [
            {
                "role": "developer",
                "content": (
                    "You are a LaTeX formatting assistant. Convert the given text "
                    "into clean LaTeX markup. Use \\subsection, \\textbf, itemize/enumerate "
                    "environments, and \\begin{table} where appropriate. Do NOT wrap in "
                    "\\begin{document} or add a preamble – only produce the body content "
                    "for this section."
                ),
            },
            {"role": "user", "content": draft},
        ]

        latex_fragment = _chat(messages, max_completion_tokens=4096, reasoning_effort="low")
        latex_sections[item_id] = latex_fragment

    # Assemble the full document
    final_latex = sections_to_latex(consort_items, latex_sections)

    logger.info("Generated final LaTeX document: %d chars", len(final_latex))

    return {
        "latex_sections": latex_sections,
        "final_latex": final_latex,
    }
