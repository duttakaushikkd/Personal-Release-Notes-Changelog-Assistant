"""Retrieval utilities for the project.

Provides a lightweight, dependency-free TF-IDF based retriever that loads
chunks from `data/chunks.json` and returns the top-k most relevant chunks
for a query. This avoids heavy vector libraries and works out-of-the-box.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import Dict, List, Tuple


def _tokenize(text: str) -> List[str]:
	return re.findall(r"\w+", text.lower())


def _compute_idf(docs_tokens: List[List[str]]) -> Dict[str, float]:
	N = len(docs_tokens)
	df = Counter()
	for tokens in docs_tokens:
		df.update(set(tokens))
	idf = {term: math.log((N / (1 + df_val))) for term, df_val in df.items()}
	return idf


def _tf(tokens: List[str]) -> Dict[str, float]:
	c = Counter(tokens)
	total = len(tokens) if tokens else 1
	return {t: v / total for t, v in c.items()}


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
	tf_vals = _tf(tokens)
	return {t: tf_vals.get(t, 0.0) * idf.get(t, 0.0) for t in tf_vals}


def _cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
	# dot / (||a|| * ||b||)
	dot = 0.0
	for k, v in a.items():
		dot += v * b.get(k, 0.0)
	norm_a = math.sqrt(sum(v * v for v in a.values()))
	norm_b = math.sqrt(sum(v * v for v in b.values()))
	if norm_a == 0 or norm_b == 0:
		return 0.0
	return dot / (norm_a * norm_b)


def load_chunks(path: str = "data/chunks.json") -> List[Dict]:
	if not os.path.exists(path):
		raise FileNotFoundError(f"Chunks file not found: {path}")
	with open(path, "r", encoding="utf-8") as f:
		return json.load(f)


def retrieve(query: str, top_k: int = 5, data_path: str = "data/chunks.json") -> List[Dict]:
	"""Return top_k chunk dicts ordered by relevance to query.

	Each returned dict is the original chunk dict augmented with a `score`
	float in the 0..1 range.
	"""
	chunks = load_chunks(data_path)
	docs_tokens = [_tokenize(c.get("text", "")) for c in chunks]
	idf = _compute_idf(docs_tokens)

	docs_vecs = [_tfidf_vector(tokens, idf) for tokens in docs_tokens]
	q_tokens = _tokenize(query)
	q_vec = _tfidf_vector(q_tokens, idf)

	scores: List[Tuple[int, float]] = []
	for i, v in enumerate(docs_vecs):
		sim = _cosine_sim(q_vec, v)
		scores.append((i, sim))

	scores.sort(key=lambda x: x[1], reverse=True)
	results: List[Dict] = []
	for idx, score in scores[:top_k]:
		chunk = dict(chunks[idx])
		chunk["score"] = float(score)
		results.append(chunk)
	return results


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Simple retrieval from chunk JSON")
	parser.add_argument("--query", required=True, help="Query string")
	parser.add_argument("--topk", type=int, default=5, help="Number of results")
	parser.add_argument("--data", default="data/chunks.json", help="Path to chunks.json")
	args = parser.parse_args()
	res = retrieve(args.query, top_k=args.topk, data_path=args.data)
	for r in res:
		print(f"[{r['score']:.4f}] id={r.get('id')} text={r.get('text')[:200].replace('\n',' ')}")


