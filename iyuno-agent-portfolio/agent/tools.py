"""Tool implementations the agent can call: calculator, doc search, policy lookup.

Each tool is a small, strictly-validated function with an explicit JSON-schema
description, following the least-privilege guidance summarized in
data/raw/least-privilege-agent-permissions.md and the tool-calling pattern in
data/raw/tool-calling-agents.md: the agent only ever gets back what the tool
returns, never raw system access.
"""
from __future__ import annotations

import ast
import operator
import time
from dataclasses import dataclass
from typing import Any, Callable

from agent.retriever import get_retriever

# ---- Tool 1: calculator -----------------------------------------------------

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


class CalculatorError(ValueError):
    pass


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise CalculatorError(f"Unsupported expression element: {ast.dump(node)}")


def calculator(expression: str) -> dict:
    """Evaluate a basic arithmetic expression safely (+ - * / % ** and parens only)."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
        return {"ok": True, "result": result}
    except (SyntaxError, CalculatorError, ZeroDivisionError, TypeError) as e:
        return {"ok": False, "error": str(e)}


# ---- Tool 2: document search (wraps the RAG retriever) ---------------------


def doc_search(query: str, k: int = 4) -> dict:
    """Search the ingested public document corpus and return cited passages."""
    retriever = get_retriever()
    hits = retriever.search(query, k=k)
    return {
        "ok": True,
        "results": [
            {
                "chunk_id": h.chunk_id,
                "title": h.title,
                "score": round(h.score, 4),
                "excerpt": h.text[:400],
            }
            for h in hits
        ],
    }


# ---- Tool 3: policy / document lookup by exact id --------------------------


def policy_lookup(doc_id: str) -> dict:
    """Look up a specific ingested document by its doc_id (e.g. 'owasp-top10-overview')."""
    retriever = get_retriever()
    matches = [c for c in retriever.chunks if c.doc_id == doc_id]
    if not matches:
        known = sorted({c.doc_id for c in retriever.chunks})
        return {"ok": False, "error": f"unknown doc_id '{doc_id}'", "known_doc_ids": known}
    return {
        "ok": True,
        "doc_id": doc_id,
        "title": matches[0].title,
        "retrieved_date": matches[0].retrieved_date,
        "license": matches[0].license,
        "chunks": [m.text for m in matches],
    }


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., dict]


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "calculator": ToolSpec(
        name="calculator",
        description="Evaluate an arithmetic expression. Use for numeric questions (latency math, cost totals, percentages).",
        parameters={"expression": "string, e.g. '(120*0.02)+15'"},
        fn=calculator,
    ),
    "doc_search": ToolSpec(
        name="doc_search",
        description="Semantic search over the ingested public tech/security corpus. Returns top-k cited passages.",
        parameters={"query": "string", "k": "int, default 4"},
        fn=doc_search,
    ),
    "policy_lookup": ToolSpec(
        name="policy_lookup",
        description="Fetch the full content of one known document by its exact doc_id.",
        parameters={"doc_id": "string"},
        fn=policy_lookup,
    ),
}

# Simple in-memory call log for observability (per data/raw/logging-and-observability.md)
CALL_LOG: list[dict[str, Any]] = []


def call_tool(name: str, **kwargs) -> dict:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Unknown tool '{name}'. Known tools: {list(TOOL_REGISTRY)}")
    spec = TOOL_REGISTRY[name]
    start = time.perf_counter()
    result = spec.fn(**kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    CALL_LOG.append({"tool": name, "args": kwargs, "elapsed_ms": round(elapsed_ms, 2), "ok": result.get("ok", True)})
    return result
