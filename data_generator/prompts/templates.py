"""Prompt templates for generating CONSORT-aligned trial documents."""

from typing import Any, Dict, Optional

from data_generator.consort_sections import SectionSpec

SYSTEM_PROMPT = """You are an expert medical writer generating realistic clinical trial documentation for a Phase 3 randomized controlled trial. Your output will be used by CliniRepGen to test automated CONSORT 2025-aligned report generation. Write in clear, formal scientific English. Use numbered or uppercase section headings exactly as specified so that document parsers can split sections. Do not invent trial identifiers or patient data that could be confused with real trials; keep everything clearly synthetic. Be consistent with the trial context provided."""


def _trial_context_str(context: Optional[Dict[str, Any]]) -> str:
    if not context:
        return "No specific trial context provided; use a generic Phase 3 RCT (e.g. drug vs placebo, 300-400 participants, 24-week treatment)."
    parts = []
    if context.get("indication"):
        parts.append(f"Indication: {context['indication']}")
    if context.get("drug_name"):
        parts.append(f"Intervention: {context['drug_name']}")
    if context.get("design"):
        parts.append(f"Design: {context['design']}")
    if context.get("n_participants"):
        parts.append(f"Planned sample size: {context['n_participants']}")
    if context.get("brief_title"):
        parts.append(f"Brief title: {context['brief_title']}")
    if not parts:
        return "Generic Phase 3 RCT context."
    return "\n".join(parts)


def build_protocol_section_prompt(
    section: SectionSpec,
    trial_context: Optional[Dict[str, Any]] = None,
    extra_instruction: Optional[str] = None,
) -> str:
    """Build user prompt for one Protocol section."""
    context_str = _trial_context_str(trial_context)
    s = f"""Generate the following section for a clinical trial protocol. Align with CONSORT 2025 where relevant (items: {', '.join(section.consort_item_ids) or 'general'}).

Trial context:
{context_str}

Section heading (use exactly this at the start of your response):
{section.heading}

Section purpose: {section.short_description}

Target length: approximately {section.target_words} words. Write only the section content (include the heading as the first line), no preamble or meta-commentary."""
    if extra_instruction:
        s += f"\n\n{extra_instruction}"
    return s


def build_sap_section_prompt(
    section: SectionSpec,
    trial_context: Optional[Dict[str, Any]] = None,
    extra_instruction: Optional[str] = None,
) -> str:
    """Build user prompt for one SAP section."""
    context_str = _trial_context_str(trial_context)
    s = f"""Generate the following section for a Statistical Analysis Plan (SAP) for a clinical trial.

Trial context:
{context_str}

Section heading (use exactly this at the start of your response):
{section.heading}

Section purpose: {section.short_description}

Target length: approximately {section.target_words} words. Write only the section content (include the heading as the first line), no preamble."""
    if extra_instruction:
        s += f"\n\n{extra_instruction}"
    return s


def build_summary_tables_section_prompt(
    section: SectionSpec,
    trial_context: Optional[Dict[str, Any]] = None,
    extra_instruction: Optional[str] = None,
) -> str:
    """Build user prompt for one Summary Tables/Listings section."""
    context_str = _trial_context_str(trial_context)
    s = f"""Generate the following summary table or listing section for a clinical study report. Use realistic-looking (synthetic) numbers and formatting. You may use markdown tables or structured text.

Trial context:
{context_str}

Section heading (use exactly this at the start of your response):
{section.heading}

Section purpose: {section.short_description}

Target length: approximately {section.target_words} words. Write only the section content (include the heading as the first line). Use clear column headers and consistent units."""
    if extra_instruction:
        s += f"\n\n{extra_instruction}"
    return s
