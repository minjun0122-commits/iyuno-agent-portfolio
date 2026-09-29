"""Email summary of what needs attention (replaces the n8n new-order alert).

Configure with env vars; if SMTP is not configured the summary is only printed.
    SMARTSTORE_SMTP_HOST, SMARTSTORE_SMTP_PORT (default 587), SMARTSTORE_SMTP_USER,
    SMARTSTORE_SMTP_PASSWORD (e.g. a Gmail app password), SMARTSTORE_NOTIFY_TO
"""
from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage


def build_summary(results: dict) -> str | None:
    """Return a Korean summary, or None when nothing needs attention."""
    lines: list[str] = []
    orders = results.get("sync-orders") or {}
    new = orders.get("ordered") or ([p["product_order_id"] for p in orders.get("planned", [])] if orders.get("dry_run") else [])
    if new:
        lines.append(f"🛒 신규 주문 {len(new)}건: {', '.join(new)}")
    for step, r in results.items():
        for f in r.get("failed", []):
            lines.append(f"⚠️ [{step}] {f['product_order_id']}: {f['reason']} → 직접 처리 필요")
    inv = results.get("sync-inventory") or {}
    if inv.get("restocked"):
        lines.append(f"✅ 재입고: {', '.join(inv['restocked'])}")
    if inv.get("sold_out"):
        lines.append(f"⛔ 품절 처리: {', '.join(inv['sold_out'])}")
    for p in inv.get("planned", []):
        for c in p["changes"]:
            if c.get("error"):
                lines.append(f"⚠️ 상품 {p['origin_product_no']} 옵션 '{c['option']}' 을 찾을 수 없음 (product_map 확인)")
    shipped = (results.get("sync-tracking") or {}).get("shipped", [])
    if shipped:
        lines.append(f"🚚 발송처리 {len(shipped)}건")
    drafts = (results.get("draft-cs") or {}).get("drafted", [])
    if drafts:
        lines.append(f"💬 미답변 문의 {len(drafts)}건 (초안 작성됨)")
    return "\n".join(lines) if lines else None


def send(summary: str, subject: str = "[홈리빙클럽] 스토어 알림") -> bool:
    env = os.environ.get
    host, to = env("SMARTSTORE_SMTP_HOST"), env("SMARTSTORE_NOTIFY_TO")
    if not (host and to):
        print(summary, file=sys.stderr)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = env("SMARTSTORE_SMTP_USER") or to
    msg["To"] = to
    msg.set_content(summary)
    with smtplib.SMTP(host, int(env("SMARTSTORE_SMTP_PORT", "587")), timeout=20) as s:
        s.starttls()
        if env("SMARTSTORE_SMTP_USER"):
            s.login(env("SMARTSTORE_SMTP_USER"), env("SMARTSTORE_SMTP_PASSWORD", ""))
        s.send_message(msg)
    return True
