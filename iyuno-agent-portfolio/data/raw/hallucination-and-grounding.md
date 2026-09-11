---
title: "Hallucination and grounding in generative models"
source_topic: "Hallucination and grounding in generative models"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

A hallucination is a model output that is fluent and confident but not
supported by any real source, whether that source is the model's training
data or, in a RAG system, the retrieved context. Grounding techniques reduce
hallucination by making the model's answer traceable to evidence: requiring
inline citations to specific retrieved chunks, instructing the model to say
it does not know when the retrieved evidence is insufficient, and running a
separate faithfulness check that verifies each claim in the answer against
the cited passage. Because grounding depends on retrieval quality, a system
can still hallucinate confidently if the retriever returns irrelevant
passages that happen to be topically similar to the question, which is why
retrieval metrics and generation faithfulness are usually evaluated
separately rather than folded into a single overall accuracy number.
