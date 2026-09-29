"""Product Q&A: fetch unanswered questions and draft replies.

Drafts use Claude when ANTHROPIC_API_KEY is set and fall back to keyword
templates otherwise (same fallback pattern as agent/router.py). Posting is
off by default: an operator reviews drafts and runs with --post.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from smartstore.orders import kst_iso
from smartstore.store import Store

BASE = "/external/v1/contents/qnas"

TEMPLATES = [
    (("배송", "언제", "도착", "출고"),
     "안녕하세요, 문의 감사합니다. 주문 후 영업일 기준 1~3일 내 출고되며, 출고 후 송장번호로 배송 조회가 가능합니다."),
    (("재고", "품절", "입고"),
     "안녕하세요, 문의 감사합니다. 현재 상품 페이지에서 구매 가능한 옵션은 재고가 있는 상태입니다. 품절 시 구매 버튼이 비활성화됩니다."),
    (("교환", "반품", "환불", "취소"),
     "안녕하세요, 문의 감사합니다. 교환/반품은 상품 수령 후 7일 이내 마이페이지에서 신청하실 수 있습니다. 단순 변심의 경우 왕복 배송비가 부과됩니다."),
]
GENERIC = "안녕하세요, 문의 감사합니다. 확인 후 빠르게 답변드리겠습니다."


class QnaAPI:
    def __init__(self, client):
        self.client = client

    def unanswered(self, since: datetime, until: datetime) -> list[dict]:
        body = self.client.get(BASE, fromDate=kst_iso(since), toDate=kst_iso(until), answered="false", page=1, size=100)
        return body.get("contents", [])

    def answer(self, question_id: str, text: str) -> dict:
        return self.client.put(f"{BASE}/{question_id}", {"commentContent": text})


def template_answer(question: str) -> str:
    for keywords, text in TEMPLATES:
        if any(k in question for k in keywords):
            return text
    return GENERIC


def draft_answer(question: str, product_name: str = "", model: str = "claude-sonnet-5-5") -> tuple[str, str]:
    """Return (draft, mode)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return template_answer(question), "template (no ANTHROPIC_API_KEY set)"
    try:
        import anthropic  # lazy: template mode needs no extra deps

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=400,
            system=(
                "당신은 네이버 스마트스토어 판매자의 CS 담당자입니다. 고객 문의에 정중하고 짧게(3문장 이내) 한국어로 답하세요. "
                "모르는 정보(정확한 재고 수량, 도착 날짜 등)는 지어내지 말고 확인 후 안내하겠다고 답하세요. "
                "개인정보를 요구하지 마세요."
            ),
            messages=[{"role": "user", "content": f"상품: {product_name}\n문의: {question}"}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        return (text or template_answer(question)), "llm"
    except Exception:
        return template_answer(question), "template (LLM call failed, fell back)"


def draft_cs(api: QnaAPI, store: Store, model: str, post: bool = False, dry_run: bool = True,
             now=lambda: datetime.now(timezone.utc)) -> dict:
    until = now()
    report = {"ok": True, "dry_run": dry_run, "drafted": [], "posted": []}
    for q in api.unanswered(until - timedelta(days=7), until):
        qid, question = str(q["questionId"]), q.get("question", "")
        existing = store.get_draft(qid)
        if existing and existing["posted"]:
            continue
        if existing:
            text, mode = existing["draft"], existing["mode"]
        else:
            text, mode = draft_answer(question, q.get("productName", ""), model)
            if not dry_run:
                store.save_draft(qid, question, text, mode)
        report["drafted"].append({"question_id": qid, "question": question, "draft": text, "mode": mode})
        if post and not dry_run:
            api.answer(qid, text)
            store.mark_posted(qid)
            report["posted"].append(qid)
    return report
