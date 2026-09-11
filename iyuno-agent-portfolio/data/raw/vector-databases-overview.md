---
title: "Vector databases and approximate nearest neighbor search"
source_topic: "Vector databases and approximate nearest neighbor search"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

Vector databases store high-dimensional embeddings and support approximate
nearest-neighbor (ANN) search so that similarity queries return in
sub-linear time even over millions of vectors. Common indexing algorithms
include HNSW (hierarchical navigable small world graphs, which trade memory
for very fast, high-recall search), IVF (inverted file indexes that partition
the space into clusters searched selectively), and product quantization
(which compresses vectors to reduce memory at some cost to precision).
Metadata filtering lets a query combine vector similarity with structured
constraints, such as restricting results to documents from a particular
source or date range. For small corpora (thousands of chunks), an exact or
brute-force cosine-similarity search, or a classical sparse method like
TF-IDF or BM25, is often fast enough and avoids the operational overhead of a
dedicated ANN index.
