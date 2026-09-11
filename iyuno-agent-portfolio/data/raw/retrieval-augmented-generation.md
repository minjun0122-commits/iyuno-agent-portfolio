---
title: "Retrieval-Augmented Generation (RAG) design patterns"
source_topic: "Retrieval-Augmented Generation (RAG) design patterns"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

RAG systems combine a retriever, which finds relevant passages from a
document store, with a generator that composes an answer conditioned on those
passages. Standard pipelines chunk source documents into overlapping windows,
embed each chunk into a vector space, and store the vectors in an index that
supports approximate nearest-neighbor search. At query time the user question
is embedded with the same model, the top-k nearest chunks are retrieved, and
the generator is given both the question and the retrieved chunks so it can
ground its answer in them and cite the source chunk. Common evaluation
metrics include retrieval metrics such as recall@k and mean reciprocal rank,
and generation metrics such as faithfulness (whether the answer's claims are
actually supported by the retrieved text) and answer relevance. A frequent
failure mode is retrieving semantically similar but factually irrelevant
chunks, which motivates hybrid retrieval that combines dense vector search
with sparse keyword search such as BM25.
