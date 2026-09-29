"""Runs a few sample questions through the LLM (Claude API) path and writes
the answers to evaluation/llm_examples.md, so the README can link to real
LLM-mode output instead of only describing it.

Requires ANTHROPIC_API_KEY. Without it, the script exits without writing
anything, because answer_query_llm() would silently fall back to the
extractive mode and the file would not show real LLM output.

Run with:  python -m scripts.run_llm_examples
"""
from __future__ import annotations

import os
import pathlib
import sys

from agent.router import answer_query, answer_query_llm

OUT_PATH = pathlib.Path(__file__).resolve().parent.parent / "evaluation" / "llm_examples.md"

QUESTIONS = [
    "What is prompt injection?",
    "How can you defend an agent against prompt injection from retrieved documents?",
    "How do zero trust principles relate to least privilege for agent tool permissions?",
    # paraphrase question the extractive TF-IDF mode gets wrong (see eval_set.json p01)
    "How can a server stop one customer from flooding it with too many calls?",
    "What is the capital of France?",
]


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set; nothing written.")
        return 1

    lines = [
        "# LLM 모드 실행 예시",
        "",
        "`python -m scripts.run_llm_examples` 로 생성한 결과입니다. "
        "같은 질문에 대해 오프라인 추출 모드와 Claude API 모드의 답을 나란히 비교합니다.",
        "",
    ]
    for q in QUESTIONS:
        offline = answer_query(q)
        llm = answer_query_llm(q)
        lines += [
            f"## {q}",
            "",
            f"**LLM 모드** (`{llm.mode}`, {llm.latency_ms:.0f} ms)",
            "",
            llm.answer.strip(),
            "",
            f"출처: {', '.join(llm.citations) or '없음'}",
            "",
            "**오프라인 추출 모드**",
            "",
            offline.answer.strip(),
            "",
            f"출처: {', '.join(offline.citations) or '없음'}",
            "",
        ]
        if llm.mode != "llm":
            print(f"warning: LLM call fell back for {q!r} ({llm.mode})")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
