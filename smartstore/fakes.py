"""In-memory stand-ins for the Commerce API, used by tests and `jobs --mock`."""
from __future__ import annotations

from datetime import datetime

from smartstore.suppliers.base import SupplierItem
from smartstore.suppliers.mock import MockSupplier


def make_order(pid: str, sku: str, quantity: int = 1, status: str = "PAYED") -> dict:
    return {
        "order": {"orderId": f"O-{pid}"},
        "productOrder": {
            "productOrderId": pid,
            "productOrderStatus": status,
            "productName": f"상품 {sku}",
            "sellerProductCode": sku,
            "quantity": quantity,
            "shippingMemo": "문 앞에 놓아주세요",
            "shippingAddress": {"name": "홍길동", "tel1": "010-0000-0000", "zipCode": "04524",
                                "baseAddress": "서울특별시 중구 세종대로 110", "detailedAddress": "1층"},
        },
    }


class FakeOrderAPI:
    def __init__(self, orders: list[dict], reject_confirm: set[str] | None = None,
                 reject_dispatch: set[str] | None = None):
        self.orders = {o["productOrder"]["productOrderId"]: o for o in orders}
        self.reject_confirm = reject_confirm or set()
        self.reject_dispatch = reject_dispatch or set()
        self.confirmed: list[str] = []
        self.dispatched: list[dict] = []

    def changed_paid_order_ids(self, since: datetime) -> list[str]:
        return list(self.orders)

    def query(self, ids: list[str]) -> list[dict]:
        return [self.orders[i] for i in ids if i in self.orders]

    def confirm(self, ids: list[str]) -> dict:
        ok = [i for i in ids if i not in self.reject_confirm]
        self.confirmed += ok
        return {"successProductOrderIds": ok,
                "failProductOrderInfos": [{"productOrderId": i, "message": "rejected"} for i in ids if i in self.reject_confirm]}

    def dispatch(self, items: list[dict]) -> dict:
        ok = [i for i in items if i["productOrderId"] not in self.reject_dispatch]
        self.dispatched += ok
        return {"successProductOrderIds": [i["productOrderId"] for i in ok],
                "failProductOrderInfos": [{"productOrderId": i["productOrderId"], "message": "rejected"}
                                          for i in items if i["productOrderId"] in self.reject_dispatch]}


class FakeProductAPI:
    def __init__(self, products: dict[str, dict]):
        self.products = products  # origin_product_no -> {"salePrice":..., "stockQuantity":...}
        self.puts: list[tuple[str, dict]] = []

    def get_origin(self, no: str) -> dict:
        return {"originProduct": dict(self.products[no])}

    def put_origin(self, no: str, body: dict) -> dict:
        self.products[no] = body["originProduct"]
        self.puts.append((no, body))
        return {}


class FakeQnaAPI:
    def __init__(self, questions: list[dict]):
        self.questions = questions
        self.answers: dict[str, str] = {}

    def unanswered(self, since, until) -> list[dict]:
        return [q for q in self.questions if str(q["questionId"]) not in self.answers]

    def answer(self, qid: str, text: str) -> dict:
        self.answers[qid] = text
        return {}


def demo_fixtures():
    """Sample data for `python -m smartstore.jobs ... --mock`."""
    supplier = MockSupplier(items={
        "SKU-TUMBLER": SupplierItem("SKU-TUMBLER", True, 50, cost=8000, shipping_fee=3000),
        "SKU-CABLE": SupplierItem("SKU-CABLE", True, 0, cost=2500, shipping_fee=3000),
        "SKU-LAMP": SupplierItem("SKU-LAMP", True, 12, cost=15000, shipping_fee=3500),
    })
    orders = FakeOrderAPI([
        make_order("2026092900001", "SKU-TUMBLER", 2),
        make_order("2026092900002", "SKU-CABLE", 1),
        make_order("2026092900003", "SKU-LAMP", 1),
        make_order("2026092900004", "SKU-LAMP", 1, status="CANCELED"),
    ])
    products = FakeProductAPI({
        "1001": {"salePrice": 12900, "stockQuantity": 50},
        "1002": {"salePrice": 6900, "stockQuantity": 30},
        "1003": {"salePrice": 21900, "stockQuantity": 12},
    })
    product_map = [{"origin_product_no": "1001", "sku": "SKU-TUMBLER"},
                   {"origin_product_no": "1002", "sku": "SKU-CABLE"},
                   {"origin_product_no": "1003", "sku": "SKU-LAMP"}]
    qna = FakeQnaAPI([
        {"questionId": 501, "question": "언제 배송되나요?", "productName": "보온 텀블러"},
        {"questionId": 502, "question": "색상 추가 예정 있나요?", "productName": "무드등"},
    ])
    return supplier, orders, products, product_map, qna
