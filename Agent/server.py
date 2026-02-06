"""
FastAPI server bridging the UI to the CONSORT Deep Research Agent.

Endpoints
─────────
    POST /api/process    – Upload files → ingest into Qdrant → return summaries
    POST /api/generate   – Run the LangGraph agent → return LaTeX report
    GET  /api/health     – Health check

Start with:
    python server.py                  # or
    uvicorn server:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Agent-internal imports ────────────────────────────────────────────
from config import get_settings, Settings
from ingest.chunker import chunk_documents
from ingest.uploader import upload_chunks
from search.you_client import YouSearchClient
from agent.graph import build_graph, create_initial_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ──────────────────────────────────────────────────────

app = FastAPI(
    title="CONSORT Deep Research Agent API",
    description="HTTP bridge between the React UI and the LangGraph agent",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Vite dev-server, etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Response schemas ─────────────────────────────────────────────────


class SnippetOut(BaseModel):
    title: str | None = None
    description: str | None = None
    url: str | None = None


class FileSummaryOut(BaseModel):
    filename: str
    summary: str
    query: str | None = None
    snippets: list[SnippetOut] | None = None
    error: str | None = None


class ProcessResult(BaseModel):
    success: bool
    message: str
    files_processed: int
    points_stored: int
    summaries: list[FileSummaryOut]


class GenerateResult(BaseModel):
    success: bool
    message: str
    latex: str
    items_processed: int


# ── Helpers ──────────────────────────────────────────────────────────

# Extensions we can treat as plain text (covers what the UI sends)
_TEXT_EXTENSIONS = {".csv", ".md", ".json", ".xml", ".txt", ".tex"}


def _load_file_as_docs(path: Path) -> list[dict[str, Any]]:
    """
    Load a file into a list of document dicts ``{text, metadata}``.

    Falls back to plain-text loading for any extension not natively
    supported by the Agent's loader module.
    """
    suffix = path.suffix.lower()

    # Native loaders from the Agent's ingest.loader module
    if suffix == ".pdf":
        from ingest.loader import _load_pdf
        return _load_pdf(path)
    if suffix == ".docx":
        from ingest.loader import _load_docx
        return _load_docx(path)

    # Everything else: read as plain text
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return []
    return [
        {
            "text": text,
            "metadata": {
                "source_file": path.name,
                "file_type": suffix.lstrip("."),
                "page_number": 1,
            },
        }
    ]


def _summarise_text(text: str, settings: Settings) -> str:
    """Ask the LLM for a 2-3 sentence summary of *text*."""
    from openai import OpenAI

    oai = OpenAI(api_key=settings.openai_api_key)
    resp = oai.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "developer",
                "content": (
                    "You are a clinical research document summariser. "
                    "Return a concise 2-3 sentence summary."
                ),
            },
            {
                "role": "user",
                "content": f"Summarise this clinical trial document:\n\n{text[:3000]}",
            },
        ],
        max_completion_tokens=512,
        reasoning_effort="low",
    )
    return (resp.choices[0].message.content or "").strip()


def _sse(data: dict) -> str:
    """Format a dict as a Server-Sent Events ``data:`` frame."""
    return f"data: {json.dumps(data)}\n\n"


# ── Endpoints ────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/api/process", response_model=ProcessResult)
async def process_files(files: list[UploadFile] = File(...)):
    """
    1. Save uploaded files to a temp directory.
    2. Load → chunk → embed → upsert into Qdrant.
    3. Generate an LLM summary per file.
    4. Fetch You.com research snippets per file.
    5. Return everything in the shape the UI expects.
    """
    settings = get_settings()
    summaries: list[FileSummaryOut] = []
    total_points = 0
    tmp_dir = Path(tempfile.mkdtemp(prefix="agent_upload_"))

    try:
        # ── Save uploads ──────────────────────────────────────────────
        saved_paths: list[Path] = []
        for upload in files:
            dest = tmp_dir / (upload.filename or "unknown")
            dest.write_bytes(await upload.read())
            saved_paths.append(dest)

        # ── Process each file ─────────────────────────────────────────
        for fpath in saved_paths:
            file_out = FileSummaryOut(filename=fpath.name, summary="")
            try:
                documents = _load_file_as_docs(fpath)
                if not documents:
                    file_out.summary = "File was empty or could not be loaded."
                    file_out.error = "No content extracted."
                    summaries.append(file_out)
                    continue

                # Chunk
                chunks = chunk_documents(documents, chunk_size=1000, chunk_overlap=200)

                # Embed & upload (potentially slow – run in a thread)
                n_up = await asyncio.to_thread(upload_chunks, chunks, settings)
                total_points += n_up

                # Summarise via LLM
                full_text = " ".join(d["text"] for d in documents)
                file_out.summary = await asyncio.to_thread(
                    _summarise_text, full_text, settings
                )

                # You.com snippets (best-effort)
                try:
                    you = YouSearchClient(settings)
                    query = f"{fpath.stem} clinical trial"
                    file_out.query = query
                    results = await asyncio.to_thread(you.search_term, fpath.stem)
                    file_out.snippets = [
                        SnippetOut(title=r.title, description=r.snippet, url=r.url)
                        for r in results[:3]
                    ]
                except Exception as exc:
                    logger.warning("You.com search failed for %s: %s", fpath.name, exc)
                    file_out.snippets = []

            except Exception as exc:
                logger.exception("Error processing %s", fpath.name)
                file_out.error = str(exc)
                file_out.summary = f"Error processing file: {exc}"

            summaries.append(file_out)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return ProcessResult(
        success=True,
        message=f"Processed {len(summaries)} file(s).",
        files_processed=len(summaries),
        points_stored=total_points,
        summaries=summaries,
    )


@app.post("/api/generate")
async def generate_report():
    """
    Run the full CONSORT deep-research agent and stream progress via
    **Server-Sent Events** (SSE).

    Event types:
        progress  – intermediate status update
        complete  – final LaTeX payload
        error     – something went wrong
    """
    settings = get_settings()

    async def _stream():
        try:
            yield _sse({
                "type": "progress",
                "message": "Initialising research graph...",
                "progress": 0,
            })

            graph = build_graph()
            compiled = graph.compile()
            initial_state = create_initial_state(settings.consort_json_path)
            total = len(initial_state["consort_items"])

            yield _sse({
                "type": "progress",
                "message": f"Processing {total} CONSORT items – this may take several minutes...",
                "progress": 0,
                "total": total,
            })

            # Heavy work – run in a thread so we don't block the event loop
            final_state = await asyncio.to_thread(compiled.invoke, initial_state)

            latex = final_state.get("final_latex", "")
            if not latex:
                yield _sse({"type": "error", "message": "Agent finished but produced no LaTeX."})
                return

            yield _sse({
                "type": "complete",
                "message": f"Report generated successfully ({len(latex):,} chars).",
                "latex": latex,
                "items_processed": total,
            })

        except Exception as exc:
            logger.exception("Report generation failed")
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ── Serve the built Vite frontend (production) ──────────────────────
# In the Docker image the UI is built to /app/static.
# Defined AFTER all /api routes so they take priority.
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve static files; fall back to index.html for SPA routing."""
        file_path = _static_dir / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_static_dir / "index.html")

# Allow ``python server.py`` to start the server directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
