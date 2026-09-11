"""Runs the evaluation set against the agent and writes evaluation/metrics.json
plus a bar chart PNG summarizing accuracy by question type.

Metrics computed (see data/raw/agent-evaluation-metrics.md):
  - hit@k (retrieval): expected_doc_id appears among the doc_ids the
    retriever returned for that query.
  - answer_grounded: for factual/multi_hop questions, whether the agent's
    top citation's doc_id matches the expected doc (a proxy for
    faithfulness given our extractive, non-generative answer mode).
  - arithmetic_accuracy: exact match against expected_value for arithmetic
    questions.
  - refusal_accuracy: for out_of_scope questions, whether the agent
    correctly declined instead of returning a confident-looking answer.
  - latency_ms / token_cost_proxy: system metrics per query.
"""
from __future__ import annotations

import json
import pathlib
import statistics
import time

from agent.retriever import get_retriever
from agent.router import answer_query

HERE = pathlib.Path(__file__).resolve().parent
EVAL_SET_PATH = HERE / "eval_set.json"
METRICS_PATH = HERE / "metrics.json"
CHART_PATH = HERE / "metrics.png"


def _token_cost_proxy(text: str) -> int:
    """Rough token-count proxy (chars/4) so cost is trackable with zero
    external dependency on a real tokenizer or paid API."""
    return max(1, len(text) // 4)


def run() -> dict:
    with EVAL_SET_PATH.open(encoding="utf-8") as f:
        eval_set = json.load(f)

    retriever = get_retriever()

    per_question = []
    for item in eval_set:
        query = item["query"]
        start = time.perf_counter()
        resp = answer_query(query)
        latency_ms = (time.perf_counter() - start) * 1000

        row = {
            "id": item["id"],
            "type": item["type"],
            "query": query,
            "latency_ms": round(latency_ms, 2),
            "token_cost_proxy": _token_cost_proxy(query) + _token_cost_proxy(resp.answer),
            "answer": resp.answer,
            "citations": resp.citations,
        }

        if item["type"] == "arithmetic":
            try:
                got = float(resp.answer.split("=")[-1].strip())
            except ValueError:
                got = None
            row["correct"] = got is not None and abs(got - item["expected_value"]) < 1e-6
        elif item["type"] == "out_of_scope":
            declined_phrases = ["don't have enough", "don't know", "not able to", "cannot"]
            row["correct"] = any(p in resp.answer.lower() for p in declined_phrases)
        else:  # factual / multi_hop
            hits = retriever.search(query, k=4)
            retrieved_doc_ids = {h.doc_id for h in hits}
            row["hit_at_k"] = item["expected_doc_id"] in retrieved_doc_ids
            top_cited_doc = resp.citations[0].split("::")[0] if resp.citations else None
            row["correct"] = top_cited_doc == item["expected_doc_id"]

        per_question.append(row)

    def _avg(key, rows):
        vals = [r[key] for r in rows if key in r]
        return round(statistics.mean(vals), 4) if vals else None

    factual_rows = [r for r in per_question if r["type"] in ("factual", "multi_hop")]
    arith_rows = [r for r in per_question if r["type"] == "arithmetic"]
    oos_rows = [r for r in per_question if r["type"] == "out_of_scope"]

    summary = {
        "n_questions": len(per_question),
        "hit_at_4": _avg("hit_at_k", factual_rows),
        "faithfulness_proxy": (
            round(sum(1 for r in factual_rows if r["correct"]) / len(factual_rows), 4) if factual_rows else None
        ),
        "arithmetic_accuracy": (
            round(sum(1 for r in arith_rows if r["correct"]) / len(arith_rows), 4) if arith_rows else None
        ),
        "refusal_accuracy": (
            round(sum(1 for r in oos_rows if r["correct"]) / len(oos_rows), 4) if oos_rows else None
        ),
        "avg_latency_ms": _avg("latency_ms", per_question),
        "p95_latency_ms": (
            round(sorted(r["latency_ms"] for r in per_question)[int(len(per_question) * 0.95) - 1], 2)
            if per_question
            else None
        ),
        "avg_token_cost_proxy": _avg("token_cost_proxy", per_question),
    }

    result = {"summary": summary, "per_question": per_question}
    with METRICS_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    _plot(summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return result


def _plot(summary: dict) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping metrics.png")
        return

    labels = ["hit@4", "faithfulness", "arithmetic", "refusal"]
    values = [
        summary["hit_at_4"] or 0,
        summary["faithfulness_proxy"] or 0,
        summary["arithmetic_accuracy"] or 0,
        summary["refusal_accuracy"] or 0,
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(labels, values, color=["#4C6EF5", "#12B886", "#F59F00", "#E64980"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("agentic-knowledge-triage — evaluation summary")
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center")
    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=150)
    print(f"Saved chart to {CHART_PATH}")


if __name__ == "__main__":
    run()
