"""Prompt templates for Protocol, SAP, and Summary Tables."""

from data_generator.prompts.templates import (
    build_protocol_section_prompt,
    build_sap_section_prompt,
    build_summary_tables_section_prompt,
    SYSTEM_PROMPT,
)

__all__ = [
    "SYSTEM_PROMPT",
    "build_protocol_section_prompt",
    "build_sap_section_prompt",
    "build_summary_tables_section_prompt",
]
