"""Inventory/price sync: supplier stock & cost -> SmartStore origin product price & stock.

Supports products with option combinations (e.g. one color = one supplier SKU):
each product_map row maps an origin product (and optionally one option) to a supplier SKU.
"""
from __future__ import annotations

import csv
import os

from smartstore.config import Settings
from smartstore.pricing import is_sellable, margin_rate, sale_price
from smartstore.suppliers.base import Supplier

BASE = "/external/v2/products/origin-products"


class ProductAPI:
    def __init__(self, client):
        self.client = client

    def get_origin(self, origin_product_no: str) -> dict:
        return self.client.get(f"{BASE}/{origin_product_no}")

    def put_origin(self, origin_product_no: str, body: dict) -> dict:
        return self.client.put(f"{BASE}/{origin_product_no}", body)


def load_product_map(path: str) -> list[dict]:
    """CSV columns: origin_product_no,sku[,option_name]

    option_name matches a combination's option names joined with "/"
    (e.g. "핑크" or "핑크/90cm"); leave it empty for products without options.
    """
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("origin_product_no") and r.get("sku")]


def _option_label(combo: dict) -> str:
    names = [combo.get(k) for k in ("optionName1", "optionName2", "optionName3", "optionName4")]
    return "/".join(n for n in names if n)


def _target_price(current: int, items: list, settings: Settings) -> tuple[int, str]:
    """Keep the seller's own price while it still earns the target margin; otherwise
    raise it to the formula price. Never lowers a price automatically."""
    live = [i for i in items if i is not None and i.available]
    if not live:
        return current, "supplier unavailable"
    worst = max(live, key=lambda i: i.cost + i.shipping_fee)  # price must cover the costliest option
    if current and margin_rate(current, worst.cost, worst.shipping_fee, settings.fee_rate) >= settings.target_margin:
        return current, "sync"
    price = sale_price(worst.cost, worst.shipping_fee, settings.fee_rate, settings.target_margin, settings.price_round_to)
    return max(price, current or 0), "price raised to target margin"


def _target_stock(item, price: int, settings: Settings) -> int:
    if item is None or not item.available:
        return 0
    if not is_sellable(price, item.cost, item.shipping_fee, settings.fee_rate, settings.min_margin):
        return 0
    return item.stock


def sync_inventory(api: ProductAPI, supplier: Supplier, settings: Settings, product_map: list[dict],
                   dry_run: bool = True) -> dict:
    report = {"ok": True, "dry_run": dry_run, "planned": [], "updated": [], "restocked": [],
              "sold_out": [], "unchanged": 0}
    groups: dict[str, list[dict]] = {}
    for row in product_map:
        groups.setdefault(str(row["origin_product_no"]), []).append(row)

    for no, rows in groups.items():
        body = api.get_origin(no)
        origin = body["originProduct"]
        items = {r["sku"]: supplier.get_item(r["sku"]) for r in rows}
        price, reason = _target_price(origin.get("salePrice") or 0, list(items.values()), settings)
        changes = []
        if price != origin.get("salePrice"):
            changes.append({"field": "salePrice", "from": origin.get("salePrice"), "to": price, "reason": reason})

        combos = (((origin.get("detailAttribute") or {}).get("optionInfo") or {}).get("optionCombinations")) or []
        by_label = {_option_label(c): c for c in combos}
        stock_targets = []  # (combo or None, label, sku, old, new)
        for r in rows:
            label = (r.get("option_name") or "").strip()
            combo = by_label.get(label) if label else None
            if label and combo is None:
                report["ok"] = False
                changes.append({"field": "option", "option": label, "error": "option not found on product"})
                continue
            old = combo.get("stockQuantity") if combo else origin.get("stockQuantity")
            new = _target_stock(items[r["sku"]], price, settings)
            stock_targets.append((combo, label, r["sku"], old, new))
            if old != new:
                changes.append({"field": "stockQuantity", "option": label or None, "sku": r["sku"], "from": old, "to": new})
            name = f"{no}{' ' + label if label else ''}"
            if not old and new:
                report["restocked"].append(name)
            elif old and not new:
                report["sold_out"].append(name)

        if not changes:
            report["unchanged"] += 1
            continue
        report["planned"].append({"origin_product_no": no, "changes": changes})
        if dry_run:
            continue
        origin["salePrice"] = price
        for combo, _label, _sku, _old, new in stock_targets:
            if combo is not None:
                combo["stockQuantity"] = new
            else:
                origin["stockQuantity"] = new
        if combos:
            origin["stockQuantity"] = sum(int(c.get("stockQuantity") or 0) for c in combos)
        api.put_origin(no, body)
        report["updated"].append(no)
    return report
