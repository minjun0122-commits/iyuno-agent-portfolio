"""Document ingestion: load raw markdown docs, chunk them, attach metadata."""
from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass, asdict

RAW_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.json"

CHUNK_SIZE = 700  # characters
CHUNK_OVERLAP = 120


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    source_topic: str
    retrieved_date: str
    license: str
    text: str


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Very small YAML-ish frontmatter parser for our own generated docs."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not m:
        return {}, raw
    meta_block, body = m.group(1), m.group(2)
    meta = {}
    for line in meta_block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"')
    return meta, body.strip()


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # try to break on sentence boundary
        window = text[start:end]
        last_period = window.rfind(". ")
        if last_period > size * 0.5 and end < len(text):
            end = start + last_period + 1
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
    return [c for c in chunks if c]


def ingest() -> list[Chunk]:
    chunks: list[Chunk] = []
    doc_paths = sorted(RAW_DIR.glob("*.md"))
    if not doc_paths:
        raise RuntimeError(f"No raw documents found in {RAW_DIR}. Run scripts/generate_corpus.py first.")
    for doc_path in doc_paths:
        doc_id = doc_path.stem
        raw = doc_path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        pieces = _chunk_text(body)
        for i, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}::chunk{i}",
                    doc_id=doc_id,
                    title=meta.get("title", doc_id),
                    source_topic=meta.get("source_topic", doc_id),
                    retrieved_date=meta.get("retrieved_date", "unknown"),
                    license=meta.get("license", "unknown"),
                    text=piece,
                )
            )
    return chunks


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    chunks = ingest()
    with CHUNKS_PATH.open("w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)
    print(f"Ingested {len(chunks)} chunks from {len(set(c.doc_id for c in chunks))} documents -> {CHUNKS_PATH}")


if __name__ == "__main__":
    main()
