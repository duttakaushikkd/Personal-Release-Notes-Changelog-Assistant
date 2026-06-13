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

    prompt = textwrap.dedent(f"""
    You are an AI assistant that produces concise release notes from developer
    artifacts. Given the user query and the following context, synthesize a
    short, organized set of release notes with headings and bullet points.

    Query: {query}

    Context:
    {context}
    """)

    # Try to use langchain_community Ollama first (if available)
    try:
        from langchain_community.llms import Ollama

        # If the user provided a model name, pass it via the model kwarg
        llm_kwargs = {"model": llm_model} if llm_model else {}
        llm = Ollama(**llm_kwargs) if llm_kwargs else Ollama()
        # The LLM may accept a simple prompt call
        res = llm(prompt)
        # llm(prompt) may return a string or an object with .to_string()
        if isinstance(res, str):
            return res
        try:
            return str(res)
        except Exception:
            return _heuristic_summarize(query, chunks)
    except Exception:
        # LLM not available or errored; use heuristic
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

