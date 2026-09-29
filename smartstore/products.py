"""Inventory/price sync: supplier stock & cost -> SmartStore origin product price & stock.

Products with options keep stock per option combination; this MVP handles
single-SKU products only (one origin product <-> one supplier SKU).
"""
from __future__ import annotations

import csv
import os

from smartstore.config import Settings
from smartstore.pricing import is_sellable, sale_price
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
    """CSV columns: origin_product_no,sku"""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("origin_product_no") and r.get("sku")]


def sync_inventory(api: ProductAPI, supplier: Supplier, settings: Settings, product_map: list[dict],
                   dry_run: bool = True) -> dict:
    report = {"ok": True, "dry_run": dry_run, "planned": [], "updated": [], "unchanged": 0}
    for row in product_map:
        no, sku = str(row["origin_product_no"]), row["sku"]
        item = supplier.get_item(sku)
        body = api.get_origin(no)
        origin = body["originProduct"]
        current = {"price": origin.get("salePrice"), "stock": origin.get("stockQuantity")}

        if item is None or not item.available:
            target = {"price": current["price"], "stock": 0}
            reason = "supplier unavailable"
        else:
            price = sale_price(item.cost, item.shipping_fee, settings.fee_rate,
                               settings.target_margin, settings.price_round_to)
            ok = is_sellable(price, item.cost, item.shipping_fee, settings.fee_rate, settings.min_margin)
            target = {"price": price, "stock": item.stock if ok else 0}
            reason = "sync" if ok else "below min margin"

        if target == current:
            report["unchanged"] += 1
            continue
        change = {"origin_product_no": no, "sku": sku, "from": current, "to": target, "reason": reason}
        report["planned"].append(change)
        if not dry_run:
            origin["salePrice"] = target["price"]
            origin["stockQuantity"] = target["stock"]
            api.put_origin(no, body)
            report["updated"].append(no)
    return report
