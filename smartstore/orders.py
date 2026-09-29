"""Order pipeline: new paid orders -> supplier stock check -> confirm -> purchase -> tracking -> dispatch.

Every write step is skipped in dry-run mode, which is the CLI default.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from smartstore.store import Store
from smartstore.suppliers.base import PurchaseRequest, Supplier, SupplierError

KST = timezone(timedelta(hours=9))
BASE = "/external/v1/pay-order/seller/product-orders"
QUERY_BATCH = 300  # max productOrderIds per query call
CURSOR_KEY = "orders.last_changed_from"


def kst_iso(dt: datetime) -> str:
    return dt.astimezone(KST).isoformat(timespec="milliseconds")


class OrderAPI:
    """Order endpoints of the Naver Commerce API (paths per the Commerce API docs)."""

    def __init__(self, client):
        self.client = client

    def changed_paid_order_ids(self, since: datetime) -> list[str]:
        ids: list[str] = []
        params = {"lastChangedFrom": kst_iso(since), "lastChangedType": "PAYED"}
        while True:
            data = self.client.get(f"{BASE}/last-changed-statuses", **params).get("data") or {}
            ids += [s["productOrderId"] for s in data.get("lastChangeStatuses", [])]
            more = data.get("more")
            if not more:
                return ids
            params = {**params, "lastChangedFrom": more["moreFrom"], "moreSequence": more["moreSequence"]}

    def query(self, product_order_ids: list[str]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(product_order_ids), QUERY_BATCH):
            batch = product_order_ids[i:i + QUERY_BATCH]
            out += self.client.post(f"{BASE}/query", {"productOrderIds": batch}).get("data", [])
        return out

    def confirm(self, product_order_ids: list[str]) -> dict:
        return self.client.post(f"{BASE}/confirm", {"productOrderIds": product_order_ids}).get("data", {})

    def dispatch(self, items: list[dict]) -> dict:
        return self.client.post(f"{BASE}/dispatch", {"dispatchProductOrders": items}).get("data", {})


def _recipient(detail: dict) -> dict:
    addr = detail["productOrder"].get("shippingAddress") or {}
    return {
        "name": addr.get("name", ""),
        "tel": addr.get("tel1", ""),
        "zip": addr.get("zipCode", ""),
        "address": addr.get("baseAddress", ""),
        "detail": addr.get("detailedAddress", ""),
    }


def _sku(po: dict) -> str:
    return po.get("sellerProductCode") or po.get("optionManageCode") or ""


def _failed_ids(result: dict) -> dict[str, str]:
    return {
        f["productOrderId"]: f.get("message") or f.get("code") or "rejected"
        for f in result.get("failProductOrderInfos", [])
    }


class OrderSync:
    def __init__(self, api: OrderAPI, supplier: Supplier, store: Store, dry_run: bool = True,
                 now=lambda: datetime.now(timezone.utc)):
        self.api = api
        self.supplier = supplier
        self.store = store
        self.dry_run = dry_run
        self.now = now

    # ---- step 1: new orders -> confirm -> purchase --------------------------
    def sync_orders(self) -> dict:
        run_started = self.now()
        cursor = self.store.get_kv(CURSOR_KEY)
        since = datetime.fromisoformat(cursor) if cursor else run_started - timedelta(hours=1)
        since = max(since, run_started - timedelta(hours=24))  # API only allows a 24h window

        new_ids = [i for i in self.api.changed_paid_order_ids(since) if self.store.get_order(i) is None]
        # Orders confirmed on a previous run but never purchased (e.g. crash in between)
        resume_ids = [o["product_order_id"] for o in self.store.orders_by_status("CONFIRMED")]
        details = {d["productOrder"]["productOrderId"]: d for d in self.api.query(new_ids + resume_ids)}

        report = {"ok": True, "dry_run": self.dry_run, "planned": [], "confirmed": [], "ordered": [], "failed": []}
        to_confirm: list[str] = []
        for pid in new_ids:
            d = details.get(pid)
            if d is None:
                continue
            po = d["productOrder"]
            if po.get("productOrderStatus") != "PAYED":
                continue  # cancelled or already handled elsewhere
            sku, qty = _sku(po), int(po.get("quantity", 1))
            item = self.supplier.get_item(sku)
            if item is None or not item.available or item.stock < qty:
                reason = f"supplier out of stock for sku={sku!r}"
                report["failed"].append({"product_order_id": pid, "reason": reason})
                if not self.dry_run:
                    self.store.upsert_order(pid, "FAILED", sku=sku, quantity=qty, reason=reason)
                continue
            report["planned"].append({"product_order_id": pid, "sku": sku, "quantity": qty})
            to_confirm.append(pid)

        if self.dry_run:
            return report

        if to_confirm:
            result = self.api.confirm(to_confirm)
            failed = _failed_ids(result)
            for pid in to_confirm:
                po = details[pid]["productOrder"]
                if pid in failed:
                    self.store.upsert_order(pid, "FAILED", sku=_sku(po), quantity=po.get("quantity"),
                                            reason=f"confirm failed: {failed[pid]}")
                    report["failed"].append({"product_order_id": pid, "reason": failed[pid]})
                else:
                    self.store.upsert_order(pid, "CONFIRMED", sku=_sku(po), quantity=po.get("quantity"))
                    report["confirmed"].append(pid)

        for row in self.store.orders_by_status("CONFIRMED"):
            pid = row["product_order_id"]
            d = details.get(pid)
            if d is None:
                continue
            po = d["productOrder"]
            req = PurchaseRequest(pid, _sku(po), int(po.get("quantity", 1)), _recipient(d), po.get("shippingMemo", ""))
            try:
                soid = self.supplier.place_order(req)
            except SupplierError as e:
                self.store.upsert_order(pid, "FAILED", reason=f"purchase failed: {e}")
                report["failed"].append({"product_order_id": pid, "reason": str(e)})
                continue
            self.store.upsert_order(pid, "ORDERED", supplier_order_id=soid)
            report["ordered"].append(pid)

        self.store.set_kv(CURSOR_KEY, run_started.isoformat())
        return report

    # ---- step 2: supplier tracking -> dispatch -----------------------------
    def sync_tracking(self) -> dict:
        report = {"ok": True, "dry_run": self.dry_run, "planned": [], "shipped": [], "failed": []}
        items, tracking_by_id = [], {}
        for row in self.store.orders_by_status("ORDERED"):
            t = self.supplier.get_tracking(row["supplier_order_id"])
            if t is None:
                continue
            pid = row["product_order_id"]
            tracking_by_id[pid] = t
            items.append({
                "productOrderId": pid,
                "deliveryMethod": "DELIVERY",
                "deliveryCompanyCode": t.courier_code,
                "trackingNumber": t.tracking_number,
                "dispatchDate": kst_iso(self.now()),
            })
        report["planned"] = [i["productOrderId"] for i in items]
        if self.dry_run or not items:
            return report

        failed = _failed_ids(self.api.dispatch(items))
        for pid, t in tracking_by_id.items():
            if pid in failed:
                # stay ORDERED so the next run retries; keep the reason for the operator
                self.store.upsert_order(pid, "ORDERED", reason=f"dispatch failed: {failed[pid]}")
                report["failed"].append({"product_order_id": pid, "reason": failed[pid]})
            else:
                self.store.upsert_order(pid, "SHIPPED", courier_code=t.courier_code,
                                        tracking_number=t.tracking_number, reason=None)
                report["shipped"].append(pid)
        return report
