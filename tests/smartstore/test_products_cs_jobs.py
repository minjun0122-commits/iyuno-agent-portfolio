import csv

from smartstore.config import Settings
from smartstore.cs import draft_answer, draft_cs, template_answer
from smartstore.fakes import FakeProductAPI, FakeQnaAPI
from smartstore.jobs import run
from smartstore.products import sync_inventory
from smartstore.store import Store
from smartstore.suppliers.base import PurchaseRequest, SupplierItem
from smartstore.suppliers.csv_supplier import CSVSupplier
from smartstore.suppliers.mock import MockSupplier


def test_inventory_sync_updates_price_and_zeroes_unavailable():
    supplier = MockSupplier(items={"A": SupplierItem("A", True, 7, cost=8000, shipping_fee=3000),
                                   "B": SupplierItem("B", False, 0, cost=1000)})
    api = FakeProductAPI({"1": {"salePrice": 1, "stockQuantity": 1}, "2": {"salePrice": 5000, "stockQuantity": 9}})
    pm = [{"origin_product_no": "1", "sku": "A"}, {"origin_product_no": "2", "sku": "B"}]

    dry = sync_inventory(api, supplier, Settings(), pm, dry_run=True)
    assert len(dry["planned"]) == 2 and api.puts == []

    sync_inventory(api, supplier, Settings(), pm, dry_run=False)
    assert api.products["1"]["stockQuantity"] == 7
    assert api.products["1"]["salePrice"] > 11000
    assert api.products["2"]["stockQuantity"] == 0
    assert sync_inventory(api, supplier, Settings(), pm, dry_run=False)["unchanged"] == 2


def test_cs_template_fallback_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, mode = draft_answer("언제 배송되나요?")
    assert mode.startswith("template") and "출고" in text
    assert template_answer("무엇이든") == template_answer("???")


def test_cs_posts_only_with_apply_and_post(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    api, store = FakeQnaAPI([{"questionId": 1, "question": "반품 되나요?"}]), Store()
    draft_cs(api, store, "m", post=True, dry_run=True)
    assert api.answers == {}
    draft_cs(api, store, "m", post=False, dry_run=False)
    assert api.answers == {} and store.get_draft("1")["posted"] == 0
    draft_cs(api, store, "m", post=True, dry_run=False)
    assert "교환" in api.answers["1"] and store.get_draft("1")["posted"] == 1


def test_csv_supplier_roundtrip(tmp_path):
    inv, out, trk = tmp_path / "inv.csv", tmp_path / "out.csv", tmp_path / "trk.csv"
    inv.write_text("sku,available,stock,cost,shipping_fee\nA,1,3,5000,3000\n", encoding="utf-8")
    s = CSVSupplier(str(inv), str(out), str(trk))
    assert s.get_item("A").cost == 5000 and s.get_item("Z") is None
    soid = s.place_order(PurchaseRequest("P1", "A", 1, {"name": "홍길동"}))
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert rows[0]["name"] == "홍길동" and rows[0]["supplier_order_id"] == soid
    assert s.get_tracking(soid) is None
    trk.write_text(f"supplier_order_id,courier_code,tracking_number\n{soid},CJGLS,123\n", encoding="utf-8")
    assert s.get_tracking(soid).tracking_number == "123"


def test_jobs_mock_all(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    results = run(["all", "--mock", "--apply"])
    assert results["sync-orders"]["ordered"] == ["2026092900001", "2026092900003"]
    assert results["sync-tracking"]["shipped"] == ["2026092900001", "2026092900003"]
    assert len(results["draft-cs"]["drafted"]) == 2
