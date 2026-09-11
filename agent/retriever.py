"""TF-IDF based retriever with cosine similarity search + citation metadata.

Uses scikit-learn's TfidfVectorizer as a dependency-light, fully offline
"embedding" backend so the whole pipeline runs without any API key. The
retriever interface is intentionally narrow (fit / search) so a dense neural
embedding backend (OpenAI, sentence-transformers, etc.) could be swapped in
later without touching the rest of the agent.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from agent.ingest import CHUNKS_PATH, Chunk


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    score: float


class Retriever:
    def __init__(self, chunks: list[Chunk] | None = None):
        if chunks is None:
            chunks = self._load_chunks()
        self.chunks = chunks
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        corpus = [c.text for c in self.chunks]
        if not corpus:
            raise RuntimeError("No chunks to index. Run agent/ingest.py first.")
        self._matrix = self._vectorizer.fit_transform(corpus)

    @staticmethod
    def _load_chunks() -> list[Chunk]:
        if not CHUNKS_PATH.exists():
            raise RuntimeError(f"{CHUNKS_PATH} not found. Run `python -m agent.ingest` first.")
        with CHUNKS_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
        return [Chunk(**r) for r in raw]

    def search(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        q_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        top_idx = sims.argsort()[::-1][:k]
        results = []
        for idx in top_idx:
            c = self.chunks[idx]
            results.append(
                RetrievedChunk(
                    chunk_id=c.chunk_id,
                    doc_id=c.doc_id,
                    title=c.title,
                    text=c.text,
                    score=float(sims[idx]),
                )
            )
        return results


_singleton: Retriever | None = None


def get_retriever() -> Retriever:
    global _singleton
    if _singleton is None:
        _singleton = Retriever()
    return _singleton
