# Personal Release Notes — Changelog Assistant

Small single-process example that ingests developer artifacts (PDF / text),
chunks them, retrieves relevant pieces for a query, and synthesizes concise
release-notes. The project is intentionally lightweight and works without
heavy vector stores; it can optionally use a local Ollama LLM for higher-quality
generation when available.

Contents
- `backend/` — FastAPI app + core logic (chunking, retrieval, generation)
- `frontend/` — static single-page frontend (`index.html`, `app.js`)
- `data/chunks.json` — canonical persisted chunk list (always written by the
  chunker)

Architecture (quick)
- Chunking: `backend/chunking/chunking.py` reads uploads, splits text into
  chunks and always writes `data/chunks.json`. It will attempt to create
  embeddings/Chroma if optional packages are present, but failures are non-fatal.
- Retrieval: `backend/retrieval/retrieval.py` implements a small dependency-free
  TF-IDF retriever that reads `data/chunks.json` and returns top-k results with
  a `score` float in 0..1.
- Generation: `backend/generation/generation.py` formats retrieved chunks into a
  prompt and tries to call a local Ollama LLM via `langchain_community`. If an
  LLM is not available, it falls back to a lightweight heuristic summarizer.

Why file-system-first
- The chunker always writes `data/chunks.json` so retrieval and generation
  remain deterministic even if embeddings/vectorstores cannot be created on the
  current machine.

Frontend / Backend separation
- The static frontend (`frontend/index.html`) can be served by the backend
  (FastAPI mounts the `frontend` folder by default) or served separately (e.g.
  `python -m http.server 3000 --directory frontend`). When served separately
  the frontend reads a `meta[name="api-base"]` tag or the header input to
  determine the backend URL; this avoids editing JS for development.

Local Ollama usage
- If you have a local Ollama daemon and compatible Python client installed
  (for example via `langchain-community` / `ollama-client`), the generator will
  attempt to call it. The generator sends a strict instruction to the model to
  return a concise final answer only (no chunks or debug info).
- If the LLM call fails (missing packages, runtime error, or Ollama not
  running), the code falls back to `_heuristic_summarize` to produce a usable
  output.

Dependencies and common pitfalls
- Install the core dependencies into a fresh virtualenv:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```
- Note: some optional packages (Chroma, ollama-client) can conflict with
  `langchain` due to differing `pydantic` version ranges. To avoid painful
  resolution errors the `requirements.txt` in this repo comments out the
  optional vector/embedding packages by default. If you need them, install them
  into a dedicated environment and verify compatible versions.

Running the app (development)
1. Start the backend (serves API and can serve frontend if present):
   ```bash
   # inside the activated venv
   python -m backend.api
   # or with uvicorn explicitly
   uvicorn backend.api:app --reload --reload-dir backend --reload-dir frontend --port 8000
   ```
2. Open the UI (served by backend): http://127.0.0.1:8000/

Or run the frontend separately (useful when editing static files)
1. Start the backend as above on port 8000.
2. Option A — quick static server (Python):
   ```bash
   python3 -m http.server 3000 --directory frontend
   ```
   Open http://127.0.0.1:3000/ and enter the Backend URL (header control) or
   set `<meta name="api-base" content="http://127.0.0.1:8000" />` in
   `frontend/index.html` so the frontend will post to the correct host.

API endpoints (used by the frontend)
- POST /ingest — upload a file (multipart form; file field name `file`) and
  run the chunker. Returns JSON: {status, chunks, preview}
- POST /query — JSON {query: str, top_k: int} -> returns {query, top_k,
  results, notes}. `results` is a list of chunk dicts with `id`, `text`, and
  `score`. `notes` is the generated text (LLM or heuristic).

CLI examples
- Upload a file:
  ```bash
  curl -F "file=@./changelog.pdf" http://127.0.0.1:8000/ingest
  ```
- Query the chunks and generate notes:
  ```bash
  curl -H "Content-Type: application/json" -d '{"query":"Summarize user-visible changes","top_k":5}' http://127.0.0.1:8000/query
  ```

Developer notes
- Public function entry points used by the UI and other tools:
  - `backend.chunking.start(pdf_path)` — run chunking and write `data/chunks.json`.
  - `backend.retrieval.retrieve(query, top_k, data_path)` — return top-k chunks.
  - `backend.generation.generate_release_notes(query, chunks, llm_model=None)` —
	produce release notes (tries Ollama, falls back to heuristic).
- The code is defensive: chunking uses lazy imports and fallbacks so the server
  can run even when optional packages are missing or incompatible.
- Streamlit demo: `backend/app.py` was renamed to `backend/app.py.disabled` —
  you can restore it if you want the Streamlit flow instead of the static
  frontend.

Troubleshooting
- If the frontend's Upload button returns a 501 HTML error, you are posting to
  a static server that does not accept POST. Make sure the frontend is calling
  the backend URL (use the header input control or set the meta tag) and that
  the backend is running.
- If you see ImportError related to `pydantic.model_validator`, you are
  probably running with Pydantic v1. Install the project's requirements in a
  fresh environment so Pydantic v2 is used (or adjust package versions).

License & notes
- This project is a small example and not production hardened. Use it as a
  starting point for building a release-notes assistant; adapt and harden
  components (auth, input validation, larger LLM handling) before production.

Enjoy!

