"""
CLI entry point for the CONSORT Deep Research Agent.

Commands:
    ingest   – Load documents from a directory, chunk, embed, and upload to Qdrant.
    generate – Run the deep-research agent and produce a LaTeX report.

Usage:
    python main.py ingest   --input-dir ./docs/
    python main.py generate --output report.tex
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Ingest command ──────────────────────────────────────────────────────

def cmd_ingest(args: argparse.Namespace) -> None:
    """Run the document ingestion pipeline."""
    from config import get_settings
    from ingest.loader import load_directory
    from ingest.chunker import chunk_documents
    from ingest.uploader import upload_chunks

    settings = get_settings()
    input_dir = Path(args.input_dir)

    if not input_dir.is_dir():
        logger.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    logger.info("=== Starting ingestion from %s ===", input_dir)

    # Step 1: Load
    documents = load_directory(input_dir)
    if not documents:
        logger.warning("No documents found in %s", input_dir)
        sys.exit(0)

    # Step 2: Chunk
    chunks = chunk_documents(
        documents,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    # Step 3: Embed & upload
    n_uploaded = upload_chunks(chunks, settings)
    logger.info("=== Ingestion complete: %d chunks uploaded ===", n_uploaded)


# ── Generate command ────────────────────────────────────────────────────

def cmd_generate(args: argparse.Namespace) -> None:
    """Run the deep-research agent and produce a LaTeX report."""
    from config import get_settings
    from agent.graph import build_graph, create_initial_state

    settings = get_settings()
    output_path = Path(args.output)

    logger.info("=== Starting CONSORT report generation ===")
    logger.info("Model: %s | Reasoning effort: %s", settings.llm_model, settings.llm_reasoning_effort)

    # Build the LangGraph
    graph = build_graph()
    app = graph.compile()

    # Create initial state from consort.json
    initial_state = create_initial_state(settings.consort_json_path)

    # Run the graph
    logger.info("Processing %d CONSORT items...", len(initial_state["consort_items"]))
    final_state = app.invoke(initial_state)

    # Write output
    final_latex = final_state.get("final_latex", "")
    if not final_latex:
        logger.error("No LaTeX output produced!")
        sys.exit(1)

    output_path.write_text(final_latex, encoding="utf-8")
    logger.info("=== Report written to %s (%d chars) ===", output_path, len(final_latex))


# ── Argument parser ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CONSORT Deep Research Agent – generate clinical trial reports",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = subparsers.add_parser(
        "ingest",
        help="Ingest documents into Qdrant vector store",
    )
    p_ingest.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing clinical trial documents (PDF, DOCX, TXT)",
    )
    p_ingest.add_argument("--chunk-size", type=int, default=1000)
    p_ingest.add_argument("--chunk-overlap", type=int, default=200)
    p_ingest.set_defaults(func=cmd_ingest)

    # generate
    p_generate = subparsers.add_parser(
        "generate",
        help="Generate a CONSORT-compliant LaTeX report",
    )
    p_generate.add_argument(
        "--output",
        default="report.tex",
        help="Output path for the LaTeX file (default: report.tex)",
    )
    p_generate.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
