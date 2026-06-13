from __future__ import annotations

import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.chunking.chunking import start as chunk_start
from backend.retrieval.retrieval import retrieve
from backend.generation.generation import generate_release_notes


app = FastAPI(title="Release Notes Assistant API")

# Allow requests from the local frontend (and other origins during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ensure uploads and data dirs exist
Path("uploads").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)


@app.post("/api/chunk")
async def api_chunk(file: UploadFile = File(...)):
    """Upload a document and run the chunker on it. Returns chunk metadata."""
    filename = Path("uploads") / file.filename
    try:
        with open(filename, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    # run chunker (synchronous call) — chunk_start returns list of chunks or None
    chunks = chunk_start(str(filename))
    if chunks is None:
        raise HTTPException(status_code=500, detail="Chunking failed")

    preview = chunks[0]["text"][:800] if chunks else ""
    return JSONResponse({"status": "ok", "chunks": len(chunks), "preview": preview})


@app.post("/api/query")
async def api_query(body: dict):
    """Accept JSON {query: str, top_k: int} and return retrieved chunks + generated notes."""
    query = body.get("query")
    top_k = int(body.get("top_k", 5))
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")

    # Retrieve top-k chunks from persisted data/chunks.json
    try:
        results = retrieve(query, top_k=top_k, data_path="data/chunks.json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No chunks found. Upload a document first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

    # Generate release notes from retrieved chunks (may use local Ollama or fallback)
    try:
        notes = generate_release_notes(query, results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    return {"query": query, "top_k": top_k, "results": results, "notes": notes}


# Serve the small React-free frontend (static single page) from /frontend
if Path("frontend/index.html").exists():
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


def run():
    import uvicorn

    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()

