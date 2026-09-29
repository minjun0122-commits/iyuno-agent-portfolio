"""Supplier interface. Each wholesale site (도매꾹/도매매, 오너클랜, ...) gets an adapter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class SupplierError(RuntimeError):
    pass


@dataclass
class SupplierItem:
    sku: str
    available: bool
    stock: int
    cost: int
    shipping_fee: int = 0


@dataclass
class PurchaseRequest:
    product_order_id: str
    sku: str
    quantity: int
    recipient: dict = field(default_factory=dict)  # name, tel, zip, address, detail
    memo: str = ""


@dataclass
class Tracking:
    courier_code: str  # Naver deliveryCompanyCode, e.g. "CJGLS"
    tracking_number: str


class Supplier(Protocol):
    def get_item(self, sku: str) -> SupplierItem | None: ...

    def place_order(self, req: PurchaseRequest) -> str:
        """Place the purchase with the supplier; return the supplier-side order id."""
        ...

    def get_tracking(self, supplier_order_id: str) -> Tracking | None: ...
