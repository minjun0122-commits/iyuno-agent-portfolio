# agentic-knowledge-triage

An AI agent that reads a public technical/security document corpus and
answers questions with **RAG retrieval + citations + tool calling**, built as
evidence for the requirements listed in a real Korean job posting:

> **Iyuno — AI Agent Engineer** · Seoul · Hybrid · Full-time
> Deadline: 2026-09-30 · Requisition JR101122
> https://iyuno.wd3.myworkdayjobs.com/careers/job/seoul/ai-agent-engineer_jr101122

This repo is a coursework project ("공고 → GitHub 증거" assignment): read a
real job posting, translate each requirement line into something buildable,
and publish working, testable evidence instead of just a resume bullet.

## Job posting → feature mapping

| Job posting requirement | Where it's implemented |
|---|---|
| LLM 기반 AI Agent 시스템 설계·개발 (design/build an LLM agent system) | `agent/router.py` — multi-step router (classify → tool call → grounded answer) |
| RAG 검색·응답 시스템과 tool calling | `agent/retriever.py` (RAG) + `agent/tools.py` (calculator / doc_search / policy_lookup) |
| API·데이터베이스 통합 및 다단계 workflow | `agent/router.py::answer_query` (rule-based multi-step) and `answer_query_llm` (Claude API tool-use path) |
| 평가·피드백 루프, latency·cost·reliability 개선 | `evaluation/run_eval.py` → `evaluation/metrics.json` + `evaluation/metrics.png` |
| (전제) 정직한 한계 설명 | See **Limitations** below |

## Architecture

```
사용자 질문 → Agent / Router → RAG Retriever ──┐
                    │                          ├─→ 답변 + 출처 + feedback log
                    └────────→ Tools / APIs ────┘
```

- **Router** (`agent/router.py`): classifies each query (arithmetic / direct
  document lookup / open question) and calls at most `MAX_STEPS` tools per
  request (least-privilege cap, see `data/raw/least-privilege-agent-permissions.md`).
- **Retriever** (`agent/retriever.py`): TF-IDF + cosine similarity over 60
  chunks from 20 documents. Dependency-light and fully offline by design —
  the interface is narrow enough to swap in a dense embedding backend later.
- **Tools** (`agent/tools.py`): `calculator` (safe AST-based arithmetic,
  no `eval`), `doc_search` (wraps the retriever), `policy_lookup` (exact
  document fetch by id). Every call is logged (`CALL_LOG`) with timing.
- **Two run modes**: `answer_query()` is a deterministic, offline,
  extractive router used by tests/CI/evaluation. `answer_query_llm()` calls
  the Claude API when `ANTHROPIC_API_KEY` is set, and automatically falls
  back to the extractive router if the key is missing or the call fails.

## Install & run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) ingest the corpus into chunks.json
python -m agent.ingest

# 2) run tests
pytest -v

# 3) run the evaluation suite (36 questions) -> evaluation/metrics.json + .png
python -m evaluation.run_eval

# 4) launch the interactive demo
streamlit run demo/app.py
```

Optional: `export ANTHROPIC_API_KEY=sk-ant-...` before step 4 and toggle
"Use Claude API" in the sidebar to see the LLM-orchestrated path instead of
the offline extractive one.

## Evaluation results (36 questions, see `evaluation/eval_set.json`)

| Metric | Score | What it measures |
|---|---|---|
| hit@4 (retrieval) | 1.00 | Correct document appears in top-4 retrieved chunks |
| faithfulness proxy | 0.81 | Top-cited chunk's document exactly matches the expected document |
| arithmetic accuracy | 1.00 | Calculator tool returns the exact expected value |
| refusal accuracy | 1.00 | Agent declines out-of-scope questions instead of guessing |
| avg latency | <1 ms | Fully offline TF-IDF search, no network round trip |

Full per-question results: `evaluation/metrics.json`. Chart: `evaluation/metrics.png`.

## Limitations (honest, on purpose)

- **Retrieval backend is TF-IDF, not a neural embedding model.** It's fast
  and needs no API key, but it will miss purely semantic matches that share
  no vocabulary with the query (e.g. a synonym-only paraphrase). A dense
  embedding backend is the natural next step; `Retriever` was written with a
  narrow interface specifically so this swap doesn't touch the rest of the
  agent.
- **faithfulness proxy is 0.81, not 1.0** — on ~19% of factual questions the
  top-scored chunk came from a related-but-not-exact document (this shows up
  concretely on the two `multi_hop` questions in the eval set, which is
  expected: they're designed to span two documents).
- **The offline extractive mode doesn't truly "generate" an answer** — it
  quotes the most relevant retrieved passage verbatim with a citation. This
  is intentional (it's honest about what it's grounded in and needs no paid
  API to run in CI), but it means answer fluency is lower than the
  `answer_query_llm` path.
- **The 20-document corpus is a small, curated demo corpus** (see
  `data/SOURCES.md` for what each document summarizes and why), not a
  production-scale knowledge base.
- **No authentication/authorization layer** — this is a local/demo tool, not
  a deployed multi-tenant service; `data/raw/api-authentication-patterns.md`
  and `zero-trust-architecture.md` describe the patterns that would be
  needed before exposing this beyond a local demo.

## Data & licensing

See `data/SOURCES.md` for the full per-document topic/attribution table and
`LICENSE` (MIT) for code licensing.

## Repository layout

```
agent/        retriever, tools, router (the agent itself)
data/raw/     20-document source corpus + SOURCES.md
data/processed/  generated chunks.json (via agent/ingest.py)
evaluation/   eval_set.json, run_eval.py, metrics.json/.png (generated)
tests/        pytest suite (21 tests)
demo/         Streamlit demo app
scripts/      corpus generation script
.github/workflows/ci.yml   GitHub Actions: install → ingest → test → eval
```

## CI

[![CI](https://github.com/minjun0122-commits/iyuno-agent-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/minjun0122-commits/iyuno-agent-portfolio/actions/workflows/ci.yml)

Every push runs the full pipeline: install deps → ingest corpus → `pytest` →
`evaluation/run_eval.py`, with the metrics artifact uploaded for inspection.

## Retrospective

See `RETROSPECTIVE.md`.
