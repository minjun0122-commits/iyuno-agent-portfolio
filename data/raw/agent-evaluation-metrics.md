---
title: "Evaluating LLM agent systems"
source_topic: "Evaluating LLM agent systems"
retrieved_date: "2026-09-08"
license: "Original summary written for this coursework project; underlying topic is public/standard technical knowledge."
---

Because agent behavior spans retrieval, reasoning, and tool use, evaluation
usually blends several metric families. Retrieval quality is measured with
recall@k or hit@k (whether a relevant chunk appears in the top k results) and
mean reciprocal rank. Answer quality is measured with faithfulness (grounding
in retrieved evidence), exact-match or F1 against a reference answer when one
exists, and human or LLM-as-judge ratings for open-ended questions. Systems
metrics include latency (time to first token and total response time), cost
per query in tokens or currency, and tool-call success rate. A well-designed
evaluation set mixes factual lookup questions, multi-hop questions that
require combining two documents, and out-of-scope questions that a good agent
should decline to answer rather than hallucinate, since refusal accuracy is
itself a measurable and important metric.
