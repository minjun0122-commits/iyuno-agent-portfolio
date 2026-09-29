"""In-memory supplier used by tests and the --mock demo."""
from __future__ import annotations

from smartstore.suppliers.base import PurchaseRequest, SupplierError, SupplierItem, Tracking


class MockSupplier:
    def __init__(self, items: dict[str, SupplierItem] | None = None, fail_skus: set[str] | None = None):
        self.items = items or {}
        self.fail_skus = fail_skus or set()
        self.placed: list[PurchaseRequest] = []
        self.tracking: dict[str, Tracking] = {}

    def get_item(self, sku: str) -> SupplierItem | None:
        return self.items.get(sku)

    def place_order(self, req: PurchaseRequest) -> str:
        if req.sku in self.fail_skus:
            raise SupplierError(f"supplier rejected order for {req.sku}")
        self.placed.append(req)
        return f"MOCK-{req.product_order_id}"

    def get_tracking(self, supplier_order_id: str) -> Tracking | None:
        return self.tracking.get(supplier_order_id)

    def ship_all(self, courier_code: str = "CJGLS") -> None:
        """Simulate the supplier shipping everything placed so far."""
        for i, req in enumerate(self.placed):
            self.tracking[f"MOCK-{req.product_order_id}"] = Tracking(courier_code, f"6000{i:08d}")
