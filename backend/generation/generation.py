"""Generation utilities: synthesize release notes from retrieved chunks.

This module provides a small orchestration: given a query and retrieved
chunks (list of dicts with `text`), produce a concise set of release notes.
It will try to call a local Ollama LLM via langchain_community if available;
otherwise it falls back to a simple heuristic summarizer.
"""
from __future__ import annotations

import json
import textwrap
from typing import List, Dict, Optional


def _format_context(chunks: List[Dict], max_chars: int = 4000) -> str:
    out = []
    total = 0
    for c in chunks:
        t = c.get("text", "").strip()
        if not t:
            continue
        if total + len(t) > max_chars:
            break
        out.append(t)
        total += len(t)
    return "\n\n".join(out)


def _heuristic_summarize(query: str, chunks: List[Dict]) -> str:
    # Simple fallback summarizer: extract first sentence of each chunk and
    # compose bullet points. Works without any LLM dependencies.
    bullets = []
    for c in chunks:
        text = c.get("text", "").strip()
        if not text:
            continue
        # take up to the first sentence
        end = text.find(". ")
        if end == -1:
            end = min(120, len(text))
        bullets.append(text[: end + 1].replace("\n", " ").strip())
    header = f"Release notes (query: {query})\n"
    body = "\n".join([f"- {b}" for b in bullets[:10]])
    return header + body


def generate_release_notes(query: str, chunks: List[Dict], llm_model: Optional[str] = None) -> str:
    """Generate release notes for `query` from a list of retrieved chunks.

    - Tries to call a local Ollama LLM via langchain_community (if installed).
    - If LLM is unavailable or fails, falls back to a lightweight heuristic
      summarizer that composes bullets from chunk text.
    """
    context = _format_context(chunks)

    # Strong instruction to the LLM: return concise, final answer only.
    prompt = textwrap.dedent(f"""
    You are an AI assistant that produces concise release notes from developer
    artifacts. Given the user query and the following context, produce a
    concise, final answer only. DO NOT return source chunks, ids, metadata,
    or any extra debugging information — only the synthesized release notes
    organized with short headings and bullet points.

    Query: {query}

    Context:
    {context}
    """)

    # Try to use langchain_community Ollama first (if available)
    try:
        # Try langchain-community Ollama wrapper first (if available).
        from langchain_community.llms import Ollama

        # Explicitly request deterministic output when possible.
        llm_kwargs = {"model": llm_model} if llm_model else {}
        try:
            llm = Ollama(**llm_kwargs) if llm_kwargs else Ollama()
        except Exception:
            # Fallback to default constructor if model kwarg was unsupported
            llm = Ollama()

        # Call the LLM and attempt to extract plain text
        res = llm(prompt)
        print(res)
        # Common return shapes: string, object with .to_string(), or dict-like
        if isinstance(res, str):
            return res.strip()
        if hasattr(res, "to_string"):
            try:
                return str(res.to_string()).strip()
            except Exception:
                pass
        # dict-like responses may contain text in common fields
        try:
            if isinstance(res, dict):
                for k in ("text", "content", "response", "result"):
                    if k in res and isinstance(res[k], str):
                        return res[k].strip()
        except Exception:
            pass
        # Last resort: coerce to string
        return str(res).strip()
    except Exception:
        # LLM path unavailable — use heuristic fallback
        return _heuristic_summarize(query, chunks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate release notes from chunks")
    parser.add_argument("--query", required=True, help="User query / what to summarize")
    parser.add_argument("--chunks", default="data/chunks.json", help="Path to chunks.json")
    parser.add_argument("--model", default=None, help="Optional LLM model name to use with Ollama")
    args = parser.parse_args()

    with open(args.chunks, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(generate_release_notes(args.query, chunks, llm_model=args.model))

