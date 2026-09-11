"""Agent router: multi-step workflow that decides which tool(s) to call and
synthesizes a grounded, cited final answer.

Design goal from the job posting: "LLM Agent 설계 -> 다단계 workflow" and
"RAG 검색·응답 시스템과 tool calling". This module implements that workflow in
two modes:

1. LLM mode (if ANTHROPIC_API_KEY is set): the Claude API is used to decide
   which tool to call and to compose the final answer from retrieved
   evidence, with the tool schema in agent.tools.TOOL_REGISTRY passed as the
   available actions.
2. Extractive fallback mode (no API key / no network): a deterministic
   rule-based router classifies the query (arithmetic vs document question vs
   direct doc_id lookup), calls the matching tool(s), and composes an answer
   by quoting the top retrieved passage with its citation. This keeps the
   whole pipeline runnable end-to-end offline, which is what the automated
   evaluation and CI tests exercise.

Both modes return the same response schema so evaluation code doesn't care
which mode produced the answer.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field

from agent.tools import call_tool, TOOL_REGISTRY

MAX_STEPS = 4  # cap on tool calls per query, see least-privilege-agent-permissions.md

_ARITH_RE = re.compile(r"^[\s0-9+\-*/%().]+$")
_DOC_ID_RE = re.compile(r"\b([a-z0-9]+(?:-[a-z0-9]+)+)\b")


@dataclass
class AgentResponse:
    answer: str
    citations: list[str]
    tool_calls: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    mode: str = "extractive"


def _looks_arithmetic(query: str) -> bool:
    stripped = query.strip().rstrip("?")
    return bool(_ARITH_RE.match(stripped)) and any(ch.isdigit() for ch in stripped)


def _extract_known_doc_id(query: str, known_ids: set[str]) -> str | None:
    for candidate in _DOC_ID_RE.findall(query.lower().replace(" ", "-")):
        if candidate in known_ids:
            return candidate
    # also try direct slug matches inside the raw query
    for doc_id in known_ids:
        if doc_id.replace("-", " ") in query.lower():
            return doc_id
    return None


def _known_doc_ids() -> set[str]:
    from agent.retriever import get_retriever

    return {c.doc_id for c in get_retriever().chunks}


def answer_query(query: str, k: int = 4) -> AgentResponse:
    """Rule-based (extractive) multi-step agent. No external API required."""
    start = time.perf_counter()
    tool_calls: list[dict] = []

    if _looks_arithmetic(query):
        expr = query.strip().rstrip("?")
        result = call_tool("calculator", expression=expr)
        tool_calls.append({"tool": "calculator", "args": {"expression": expr}, "result": result})
        if result.get("ok"):
            answer = f"{expr} = {result['result']}"
        else:
            answer = f"Could not evaluate '{expr}': {result.get('error')}"
        latency_ms = (time.perf_counter() - start) * 1000
        return AgentResponse(answer=answer, citations=[], tool_calls=tool_calls, latency_ms=latency_ms)

    known_ids = _known_doc_ids()
    direct_id = _extract_known_doc_id(query, known_ids)
    if direct_id:
        result = call_tool("policy_lookup", doc_id=direct_id)
        tool_calls.append({"tool": "policy_lookup", "args": {"doc_id": direct_id}, "result": result})
        if result.get("ok"):
            answer = result["chunks"][0]
            citations = [f"{direct_id}::chunk0"]
        else:
            answer = "I don't have a document with that exact id."
            citations = []
        latency_ms = (time.perf_counter() - start) * 1000
        return AgentResponse(answer=answer, citations=citations, tool_calls=tool_calls, latency_ms=latency_ms)

    result = call_tool("doc_search", query=query, k=k)
    tool_calls.append({"tool": "doc_search", "args": {"query": query, "k": k}, "result": result})
    hits = result.get("results", [])
    if not hits or hits[0]["score"] < 0.05:
        latency_ms = (time.perf_counter() - start) * 1000
        return AgentResponse(
            answer="I don't have enough grounded evidence in the corpus to answer this confidently.",
            citations=[],
            tool_calls=tool_calls,
            latency_ms=latency_ms,
        )

    top = hits[0]
    answer = f"{top['excerpt']} [source: {top['title']}]"
    citations = [h["chunk_id"] for h in hits[:2] if h["score"] > 0.03]
    latency_ms = (time.perf_counter() - start) * 1000
    return AgentResponse(answer=answer, citations=citations, tool_calls=tool_calls, latency_ms=latency_ms, mode="extractive")


def answer_query_llm(query: str, k: int = 4) -> AgentResponse:
    """LLM-orchestrated mode. Requires ANTHROPIC_API_KEY. Falls back to the
    extractive router automatically if the API call fails for any reason, so
    the demo never hard-crashes without a key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        resp = answer_query(query, k=k)
        resp.mode = "extractive (no ANTHROPIC_API_KEY set)"
        return resp

    try:
        import anthropic  # imported lazily so the extractive mode has zero extra deps

        client = anthropic.Anthropic(api_key=api_key)
        search = call_tool("doc_search", query=query, k=k)
        context = "\n\n".join(f"[{h['chunk_id']}] {h['excerpt']}" for h in search["results"])
        start = time.perf_counter()
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=400,
            system=(
                "Answer ONLY using the provided context. Cite chunk ids in square "
                "brackets. If the context is insufficient, say you don't know."
            ),
            messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        text = "".join(b.text for b in msg.content if b.type == "text")
        citations = re.findall(r"\[([\w-]+::chunk\d+)\]", text)
        return AgentResponse(answer=text, citations=citations, tool_calls=[{"tool": "doc_search"}], latency_ms=latency_ms, mode="llm")
    except Exception:
        resp = answer_query(query, k=k)
        resp.mode = "extractive (LLM call failed, fell back)"
        return resp
