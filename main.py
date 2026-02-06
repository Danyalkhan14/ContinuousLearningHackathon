"""
Agent API: upload folder/file (CSV and text files), store embeddings in Qdrant,
research each file via You.com, return summaries.
"""
import os
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import ALLOWED_EXTENSIONS
from file_reader import file_to_chunks, is_allowed, read_file_to_text
from embeddings_qdrant import get_qdrant_client, upsert_chunks
from you_research import research_and_summarize

app = FastAPI(title="Document Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    points_stored: int
    summaries: list[dict[str, Any]]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/process", response_model=ProcessResponse)
async def process_files(files: list[UploadFile] = File(...)):
    """Accept multiple files (CSV, txt, md, etc.), store embeddings in Qdrant, research via You.com, return summaries."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    allowed = [f for f in files if f.filename and is_allowed(f.filename)]
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail=f"No allowed files. Use: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    try:
        qdrant = get_qdrant_client()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to Qdrant. Set QDRANT_IN_MEMORY=true to run without a Qdrant server. Error: {e}",
        )
    total_points = 0
    summaries = []
    processed = 0
    for upload in allowed:
        name = upload.filename or "unknown"
        if not is_allowed(name):
            continue
        try:
            content = await upload.read()
        except Exception as e:
            summaries.append({"filename": name, "summary": f"Read error: {e}", "snippets": [], "error": str(e)})
            continue
        # Chunk and store in Qdrant
        chunks_with_source = file_to_chunks(content, name)
        if chunks_with_source:
            try:
                n = upsert_chunks(qdrant, chunks_with_source)
                total_points += n
            except Exception as e:
                summaries.append({"filename": name, "summary": f"Qdrant error: {e}", "snippets": [], "error": str(e)})
                processed += 1
                continue
        # Research via You.com
        text_preview = read_file_to_text(content, name)
        result = research_and_summarize(text_preview, name)
        summaries.append({
            "filename": result["filename"],
            "summary": result["summary"],
            "query": result.get("query", ""),
            "snippets": result.get("snippets", []),
            "error": result.get("error"),
        })
        processed += 1
    return ProcessResponse(
        success=True,
        message=f"Processed {processed} file(s), stored {total_points} chunks in Qdrant.",
        files_processed=processed,
        points_stored=total_points,
        summaries=summaries,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
