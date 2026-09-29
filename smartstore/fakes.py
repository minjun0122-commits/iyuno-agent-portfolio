"""In-memory stand-ins for the Commerce API, used by tests and `jobs --mock`."""
from __future__ import annotations

import copy
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
        return {"originProduct": copy.deepcopy(self.products[no])}

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


def _pillow(stock_pink: int, stock_gray: int, stock_brown: int) -> dict:
    return {
        "salePrice": 19900,
        "stockQuantity": stock_pink + stock_gray + stock_brown,
        "detailAttribute": {"optionInfo": {"optionCombinations": [
            {"id": 1, "optionName1": "핑크", "stockQuantity": stock_pink},
            {"id": 2, "optionName1": "그레이", "stockQuantity": stock_gray},
            {"id": 3, "optionName1": "브라운", "stockQuantity": stock_brown},
        ]}},
    }


def demo_fixtures():
    """홈리빙클럽 sample data for `python -m smartstore.jobs ... --mock`.

    Costs are 총원가 (supplier price + shipping). The spice-container cost is a
    placeholder; the option SKUs (-PK/-GY/-BR) are illustrative, not OwnerClan codes.
    """
    supplier = MockSupplier(items={
        "WFGYD7O-PK": SupplierItem("WFGYD7O-PK", True, 20, cost=12480),
        "WFGYD7O-GY": SupplierItem("WFGYD7O-GY", True, 8, cost=12480),   # restocked at the supplier
        "WFGYD7O-BR": SupplierItem("WFGYD7O-BR", False, 0, cost=12480),  # still sold out
        "SPICE-STS": SupplierItem("SPICE-STS", True, 30, cost=14500),
    })
    orders = FakeOrderAPI([
        make_order("2026092900001", "WFGYD7O-PK", 1),
        make_order("2026092900002", "WFGYD7O-BR", 1),
        make_order("2026092900003", "SPICE-STS", 1),
        make_order("2026092900004", "SPICE-STS", 1, status="CANCELED"),
    ])
    products = FakeProductAPI({
        "1001": _pillow(stock_pink=20, stock_gray=0, stock_brown=0),
        "1002": {"salePrice": 22900, "stockQuantity": 30},
    })
    product_map = [{"origin_product_no": "1001", "sku": "WFGYD7O-PK", "option_name": "핑크"},
                   {"origin_product_no": "1001", "sku": "WFGYD7O-GY", "option_name": "그레이"},
                   {"origin_product_no": "1001", "sku": "WFGYD7O-BR", "option_name": "브라운"},
                   {"origin_product_no": "1002", "sku": "SPICE-STS", "option_name": ""}]
    qna = FakeQnaAPI([
        {"questionId": 501, "question": "그레이 색상 언제 입고되나요?", "productName": "고양이 바디필로우 90cm"},
        {"questionId": 502, "question": "세탁 가능한가요?", "productName": "고양이 바디필로우 90cm"},
    ])
    return supplier, orders, products, product_map, qna
