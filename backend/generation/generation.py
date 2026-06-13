"""Generate concise answers from retrieved release-note chunks."""
from __future__ import annotations

import json
import os
import re
import textwrap
import urllib.request
from typing import Dict, List, Optional


_BULLET = r"[•*-]"
_FIXED_ITEM_RE = re.compile(
    rf"(?:^|\n)\s*{_BULLET}\s*Fixed:\s*(.+?)"
    rf"(?=\n\s*{_BULLET}\s*|\n[A-Z][A-Za-z &/]+\n|$)",
    re.IGNORECASE | re.DOTALL,
)


class OllamaGenerationError(RuntimeError):
    """Raised when the local Ollama service cannot generate the final answer."""


def _format_context(chunks: List[Dict], max_chars: int = 4000) -> str:
    out = []
    total = 0
    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue
        if total + len(text) > max_chars:
            break
        out.append(text)
        total += len(text)
    return "\n\n".join(out)


def requires_full_context(query: str) -> bool:
    """Return whether a query asks for an aggregate bug-fix count."""
    normalized = " ".join(query.lower().split())
    normalized = re.sub(
        r"\b(how many)(bugs?|issues?|fix(?:ed|es)?)\b", r"\1 \2", normalized
    )
    asks_for_count = bool(
        re.search(r"\bhow many\b|\bnumber of\b|\bcount\b|\btotal\b", normalized)
    )
    concerns_fixes = bool(re.search(r"\bbugs?\b|\bfix(?:ed|es)?\b|\bissues?\b", normalized))
    return asks_for_count and concerns_fixes


def _extract_fixed_items(chunks: List[Dict]) -> List[str]:
    """Extract and deduplicate explicit `Fixed:` bullets from overlapping chunks."""
    items = {}
    for chunk in chunks:
        text = chunk.get("text", "")
        for match in _FIXED_ITEM_RE.finditer(text):
            item = " ".join(match.group(1).split()).rstrip(".")
            if item:
                items.setdefault(item.casefold(), item)
    return list(items.values())


def _response_text(response: object) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        for key in ("text", "content", "response", "result"):
            value = response.get(key)
            if isinstance(value, str):
                return value.strip()
    if hasattr(response, "to_string"):
        try:
            return str(response.to_string()).strip()
        except Exception:
            pass
    return str(response).strip()


def _call_ollama(prompt: str, llm_model: Optional[str] = None) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = llm_model or os.getenv("OLLAMA_MODEL")
    if not model:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as response:
            tags = json.load(response)
        models = [
            item
            for item in tags.get("models", [])
            if "embedding" not in item.get("capabilities", [])
            or "completion" in item.get("capabilities", [])
        ]
        if not models:
            raise RuntimeError(
                "No text-generation Ollama model is installed; set OLLAMA_MODEL "
                "after installing one"
            )
        model = models[0].get("name") or models[0].get("model")

    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return _response_text(json.load(response))


def generate_release_notes(
    query: str, chunks: List[Dict], llm_model: Optional[str] = None
) -> str:
    """Use local Ollama for the final answer."""
    context = _format_context(chunks)
    verified_facts = ""
    if requires_full_context(query):
        fixed_items = _extract_fixed_items(chunks)
        verified_facts = (
            f"There are exactly {len(fixed_items)} explicit, unique `Fixed:` bug-fix "
            "items in the release notes. Use this verified count in your answer."
        )

    prompt = textwrap.dedent(
        f"""
        You are an AI assistant answering questions about release notes.
        Answer the user's query concisely using only the supplied context.
        Return the final answer only. Do not include chunk ids, metadata, or
        debugging information.

        Verified facts:
        {verified_facts or "None provided. Derive the answer from the context."}

        Query:
        {query}

        Context:
        {context}
        """
    ).strip()

    try:
        return _call_ollama(prompt, llm_model=llm_model)
    except Exception as exc:
        print(f"[generation] Ollama unavailable or errored: {exc}")
        raise OllamaGenerationError(str(exc)) from exc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate answers from release-note chunks")
    parser.add_argument("--query", required=True, help="Question to answer")
    parser.add_argument("--chunks", default="data/chunks.json", help="Path to chunks.json")
    parser.add_argument("--model", default=None, help="Optional Ollama model name")
    args = parser.parse_args()

    with open(args.chunks, "r", encoding="utf-8") as file:
        chunks = json.load(file)

    print(generate_release_notes(args.query, chunks, llm_model=args.model))
