"""SQLite state: order state machine, sync cursors and CS drafts.

Recipient personal data (name/phone/address) is deliberately NOT stored here;
it is only passed through to the supplier when placing the purchase order.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

# NEW -> CONFIRMED -> ORDERED -> SHIPPED, or FAILED at any step (needs a human)
STATUSES = ("NEW", "CONFIRMED", "ORDERED", "SHIPPED", "FAILED")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    product_order_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    sku TEXT,
    quantity INTEGER,
    supplier_order_id TEXT,
    courier_code TEXT,
    tracking_number TEXT,
    reason TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cs_drafts (
    question_id TEXT PRIMARY KEY,
    question TEXT,
    draft TEXT,
    mode TEXT,
    posted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    # ---- orders -----------------------------------------------------------
    def get_order(self, product_order_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM orders WHERE product_order_id = ?", (product_order_id,)).fetchone()
        return dict(row) if row else None

    def upsert_order(self, product_order_id: str, status: str, **fields) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown status {status}")
        existing = self.get_order(product_order_id) or {}
        row = {**existing, **fields, "product_order_id": product_order_id, "status": status, "updated_at": _now()}
        cols = ["product_order_id", "status", "sku", "quantity", "supplier_order_id",
                "courier_code", "tracking_number", "reason", "updated_at"]
        self.conn.execute(
            f"INSERT OR REPLACE INTO orders ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [row.get(c) for c in cols],
        )
        self.conn.commit()

    def orders_by_status(self, status: str) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM orders WHERE status = ? ORDER BY updated_at", (status,)).fetchall()
        return [dict(r) for r in rows]

    # ---- key/value (sync cursors) ----------------------------------------
    def get_kv(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_kv(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    # ---- CS drafts --------------------------------------------------------
    def save_draft(self, question_id: str, question: str, draft: str, mode: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO cs_drafts (question_id, question, draft, mode, posted, updated_at) "
            "VALUES (?, ?, ?, ?, COALESCE((SELECT posted FROM cs_drafts WHERE question_id = ?), 0), ?)",
            (question_id, question, draft, mode, question_id, _now()),
        )
        self.conn.commit()

    def get_draft(self, question_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM cs_drafts WHERE question_id = ?", (question_id,)).fetchone()
        return dict(row) if row else None

    def mark_posted(self, question_id: str) -> None:
        self.conn.execute("UPDATE cs_drafts SET posted = 1, updated_at = ? WHERE question_id = ?", (_now(), question_id))
        self.conn.commit()
