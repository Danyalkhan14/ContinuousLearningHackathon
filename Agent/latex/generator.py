"""
Assemble a complete LaTeX document from CONSORT section drafts.

Takes the consort_items list and a dict of item_id → LaTeX fragments,
and produces a full .tex file ready for compilation.
"""

from __future__ import annotations

import logging
from typing import Any

from latex.templates import (
    PREAMBLE,
    BEGIN_DOCUMENT,
    END_DOCUMENT,
    SECTION_COMMANDS,
    CONSORT_TABLE_HEADER,
    CONSORT_TABLE_ROW,
    CONSORT_TABLE_FOOTER,
)

logger = logging.getLogger(__name__)


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    return text


def sections_to_latex(
    consort_items: list[dict[str, Any]],
    latex_sections: dict[str, str],
) -> str:
    """
    Assemble the full LaTeX document.

    Args:
        consort_items: List of CONSORT item dicts (id, section, topic, description).
        latex_sections: Dict mapping item id to its LaTeX body fragment.

    Returns:
        Complete LaTeX source as a string.
    """
    parts: list[str] = [PREAMBLE, "", BEGIN_DOCUMENT, ""]

    current_section = ""
    current_topic = ""

    for item in consort_items:
        item_id = item["id"]
        section_name = item["section"]
        topic = item["topic"]

        # Insert \section{} when we enter a new CONSORT section
        if section_name != current_section:
            current_section = section_name
            current_topic = ""  # reset topic
            sec_cmd = SECTION_COMMANDS.get(section_name, rf"\section{{{section_name}}}")
            parts.append("")
            parts.append(sec_cmd)

        # Insert \subsection{} when we enter a new topic within a section
        if topic != current_topic:
            current_topic = topic
            parts.append(rf"\subsection{{{topic}}}")
            parts.append(rf"\label{{sec:{item_id}}}")

        # Insert the LaTeX body for this item
        fragment = latex_sections.get(item_id, "")
        if fragment:
            parts.append("")
            parts.append(f"% --- CONSORT Item {item_id}: {topic} ---")
            parts.append(fragment)
        else:
            parts.append(f"\n% CONSORT Item {item_id}: No evidence available.\n")

    # Append the CONSORT compliance checklist table
    parts.append("")
    parts.append(CONSORT_TABLE_HEADER)
    for item in consort_items:
        row = CONSORT_TABLE_ROW.format(
            item_id=_escape_latex(item["id"]),
            section=_escape_latex(item["section"]),
            topic=_escape_latex(item["topic"]),
            description=_escape_latex(item["description"][:80] + "..."),
        )
        parts.append(row)
    parts.append(CONSORT_TABLE_FOOTER)

    parts.append("")
    parts.append(END_DOCUMENT)

    doc = "\n".join(parts)
    logger.info("Assembled LaTeX document: %d lines, %d chars", doc.count("\n"), len(doc))
    return doc
