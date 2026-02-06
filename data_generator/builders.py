"""Build Protocol, SAP, and Summary Tables documents by concatenating generated sections.

Each builder calls generate_section() for each defined section, forwarding
the GPT-5.2 reasoning_effort parameter when provided.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

from data_generator.config import Config
from data_generator.consort_sections import (
    PROTOCOL_SECTIONS,
    SAP_SECTIONS,
    SUMMARY_TABLE_SECTIONS,
)
from data_generator.openai_client import generate_section

logger = logging.getLogger(__name__)


def build_protocol(
    output_path: Path,
    trial_context: Optional[Dict[str, Any]] = None,
    trial_id: str = "trial_001",
    config: Optional[Config] = None,
    client: Optional[OpenAI] = None,
    reasoning_effort: Optional[str] = None,
) -> int:
    """
    Generate Protocol (60-80 pp) and write to output_path.

    Args:
        reasoning_effort: Optional GPT-5.2 reasoning effort level.

    Returns total word count.
    """
    config = config or Config()
    client = client or OpenAI(api_key=config.api_key)
    parts = []
    for i, section in enumerate(PROTOCOL_SECTIONS):
        logger.info("Protocol section %s/%s: %s", i + 1, len(PROTOCOL_SECTIONS), section.heading)
        text = generate_section(
            "protocol",
            section,
            trial_context,
            config=config,
            client=client,
            reasoning_effort=reasoning_effort,
        )
        parts.append(text)
    full = "\n\n".join(parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full, encoding="utf-8")
    return len(full.split())


def build_sap(
    output_path: Path,
    trial_context: Optional[Dict[str, Any]] = None,
    trial_id: str = "trial_001",
    config: Optional[Config] = None,
    client: Optional[OpenAI] = None,
    reasoning_effort: Optional[str] = None,
) -> int:
    """
    Generate SAP (20-30 pp) and write to output_path.

    Args:
        reasoning_effort: Optional GPT-5.2 reasoning effort level.

    Returns total word count.
    """
    config = config or Config()
    client = client or OpenAI(api_key=config.api_key)
    parts = []
    for i, section in enumerate(SAP_SECTIONS):
        logger.info("SAP section %s/%s: %s", i + 1, len(SAP_SECTIONS), section.heading)
        text = generate_section(
            "sap",
            section,
            trial_context,
            config=config,
            client=client,
            reasoning_effort=reasoning_effort,
        )
        parts.append(text)
    full = "\n\n".join(parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full, encoding="utf-8")
    return len(full.split())


def build_summary_tables(
    output_path: Path,
    trial_context: Optional[Dict[str, Any]] = None,
    trial_id: str = "trial_001",
    config: Optional[Config] = None,
    client: Optional[OpenAI] = None,
    reasoning_effort: Optional[str] = None,
) -> int:
    """
    Generate Summary Tables/Listings (30-40 pp) and write to output_path.

    Args:
        reasoning_effort: Optional GPT-5.2 reasoning effort level.

    Returns total word count.
    """
    config = config or Config()
    client = client or OpenAI(api_key=config.api_key)
    parts = []
    for i, section in enumerate(SUMMARY_TABLE_SECTIONS):
        logger.info(
            "Summary Tables section %s/%s: %s",
            i + 1,
            len(SUMMARY_TABLE_SECTIONS),
            section.heading,
        )
        text = generate_section(
            "summary_tables",
            section,
            trial_context,
            config=config,
            client=client,
            reasoning_effort=reasoning_effort,
        )
        parts.append(text)
    full = "\n\n".join(parts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full, encoding="utf-8")
    return len(full.split())
