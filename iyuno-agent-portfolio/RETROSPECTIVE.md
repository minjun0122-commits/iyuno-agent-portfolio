# 1-page retrospective

## What I set out to do

Turn a real job posting (Iyuno, AI Agent Engineer, requisition JR101122) into
working evidence instead of a resume line, by mapping each requirement
sentence to a piece of code I could actually run: an LLM agent that does
retrieval-augmented generation over a document corpus, calls tools in a
multi-step workflow, and is evaluated with real metrics rather than a demo
GIF alone.

## What I actually implemented

- A 20-document corpus (`data/raw/`) covering AI-agent-adjacent security and
  systems topics, chunked into 60 passages.
- A TF-IDF retriever (`agent/retriever.py`) with cosine-similarity search and
  per-chunk citation metadata.
- Three tools (`agent/tools.py`): a sandboxed calculator, a document search
  tool, and an exact-id document lookup tool — each logged for
  observability.
- A router (`agent/router.py`) that runs a multi-step workflow (classify →
  call the right tool(s) → compose a cited answer), with a rule-based
  offline mode for CI/tests and an optional Claude-API mode for real
  generation.
- An evaluation suite of 36 questions spanning factual, multi-hop,
  arithmetic, and out-of-scope categories, producing `hit@4`, a faithfulness
  proxy, arithmetic accuracy, refusal accuracy, and latency (`evaluation/`).
- 21 pytest tests and a GitHub Actions CI workflow that installs
  dependencies, ingests the corpus, runs the tests, and runs the evaluation
  on every push.
- A Streamlit demo (`demo/app.py`) that exposes both the offline and
  LLM-backed modes with a tool-call trace.

## What worked well

The offline extractive mode turned out to be the right default: it made the
whole pipeline (ingest → retrieve → answer → evaluate → test) runnable with
zero API keys and zero network calls, which is exactly what CI needs, and it
forces every "answer" to be traceable to a real chunk rather than a
plausible-sounding hallucination.

## What's still missing / next steps

- Swap the TF-IDF retriever for a dense embedding model to catch
  vocabulary-mismatch queries the current retriever misses.
- Add a feedback-loop table (per the job posting's "사용자의 수정 신호를
  재학습 데이터로 저장함") that stores user corrections for future
  re-ranking — the architecture diagram anticipates this ("+ feedback") but
  it isn't wired up to persistent storage yet.
- Record a short demo GIF/video of the Streamlit app for the submission
  checklist.
- If time allows, add a second retrieval backend (BM25) and compare hit@k
  against the current TF-IDF baseline, since `data/raw/retrieval-augmented-generation.md`
  itself recommends hybrid retrieval.
