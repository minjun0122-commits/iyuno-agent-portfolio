"""CSV-based supplier for wholesale sites that take bulk (Excel/CSV) orders.

- inventory CSV (in):  sku,available,stock,cost,shipping_fee
- outbox CSV (out):    one row per purchase, upload it to the supplier's bulk-order page
- tracking CSV (in):   supplier_order_id,courier_code,tracking_number

The outbox contains recipient personal data: delete it after uploading.
"""
from __future__ import annotations

import csv
import os

from smartstore.suppliers.base import PurchaseRequest, SupplierError, SupplierItem, Tracking

OUTBOX_FIELDS = ["supplier_order_id", "product_order_id", "sku", "quantity",
                 "name", "tel", "zip", "address", "detail", "memo"]


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "y", "yes"}


class CSVSupplier:
    def __init__(self, inventory_csv: str, outbox_csv: str, tracking_csv: str):
        self.inventory_csv = inventory_csv
        self.outbox_csv = outbox_csv
        self.tracking_csv = tracking_csv

    def _inventory(self) -> dict[str, SupplierItem]:
        if not os.path.exists(self.inventory_csv):
            raise SupplierError(f"inventory file not found: {self.inventory_csv}")
        with open(self.inventory_csv, newline="", encoding="utf-8-sig") as f:
            return {
                r["sku"]: SupplierItem(
                    sku=r["sku"],
                    available=_truthy(r.get("available", "1")),
                    stock=int(r.get("stock") or 0),
                    cost=int(r["cost"]),
                    shipping_fee=int(r.get("shipping_fee") or 0),
                )
                for r in csv.DictReader(f)
            }

    def get_item(self, sku: str) -> SupplierItem | None:
        return self._inventory().get(sku)

    def place_order(self, req: PurchaseRequest) -> str:
        supplier_order_id = f"CSV-{req.product_order_id}"
        new_file = not os.path.exists(self.outbox_csv)
        os.makedirs(os.path.dirname(self.outbox_csv) or ".", exist_ok=True)
        with open(self.outbox_csv, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=OUTBOX_FIELDS)
            if new_file:
                w.writeheader()
            w.writerow({
                "supplier_order_id": supplier_order_id,
                "product_order_id": req.product_order_id,
                "sku": req.sku,
                "quantity": req.quantity,
                "memo": req.memo,
                **{k: req.recipient.get(k, "") for k in ("name", "tel", "zip", "address", "detail")},
            })
        return supplier_order_id

    def get_tracking(self, supplier_order_id: str) -> Tracking | None:
        if not os.path.exists(self.tracking_csv):
            return None
        with open(self.tracking_csv, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["supplier_order_id"] == supplier_order_id and r.get("tracking_number"):
                    return Tracking(courier_code=r["courier_code"], tracking_number=r["tracking_number"])
        return None
