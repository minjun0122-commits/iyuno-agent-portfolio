import csv

from smartstore.config import Settings
from smartstore.cs import draft_answer, draft_cs, template_answer
from smartstore.fakes import FakeProductAPI, FakeQnaAPI
from smartstore.jobs import run
from smartstore.notify import build_summary
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

    report = sync_inventory(api, supplier, Settings(), pm, dry_run=False)
    assert api.products["1"]["stockQuantity"] == 7
    assert api.products["1"]["salePrice"] > 11000
    assert api.products["2"]["stockQuantity"] == 0
    assert report["sold_out"] == ["2"]
    assert sync_inventory(api, supplier, Settings(), pm, dry_run=False)["unchanged"] == 2


def test_inventory_never_lowers_a_price_that_meets_target_margin():
    supplier = MockSupplier(items={"A": SupplierItem("A", True, 5, cost=12480)})
    api = FakeProductAPI({"1": {"salePrice": 19900, "stockQuantity": 5}})
    report = sync_inventory(api, supplier, Settings(), [{"origin_product_no": "1", "sku": "A"}], dry_run=False)
    assert report["unchanged"] == 1 and api.puts == []


def _pillow_api(pink, gray, brown):
    return FakeProductAPI({"1": {"salePrice": 19900, "stockQuantity": pink + gray + brown, "detailAttribute": {
        "optionInfo": {"optionCombinations": [
            {"optionName1": "핑크", "stockQuantity": pink},
            {"optionName1": "그레이", "stockQuantity": gray},
            {"optionName1": "브라운", "stockQuantity": brown}]}}}})


PILLOW_MAP = [{"origin_product_no": "1", "sku": "PK", "option_name": "핑크"},
              {"origin_product_no": "1", "sku": "GY", "option_name": "그레이"},
              {"origin_product_no": "1", "sku": "BR", "option_name": "브라운"}]


def test_option_stock_sync_and_restock_detection():
    supplier = MockSupplier(items={"PK": SupplierItem("PK", True, 20, cost=12480),
                                   "GY": SupplierItem("GY", True, 8, cost=12480),
                                   "BR": SupplierItem("BR", False, 0, cost=12480)})
    api = _pillow_api(20, 0, 0)
    dry = sync_inventory(api, supplier, Settings(), PILLOW_MAP, dry_run=True)
    assert dry["restocked"] == ["1 그레이"] and api.puts == []

    sync_inventory(api, supplier, Settings(), PILLOW_MAP, dry_run=False)
    combos = api.products["1"]["detailAttribute"]["optionInfo"]["optionCombinations"]
    assert [c["stockQuantity"] for c in combos] == [20, 8, 0]
    assert api.products["1"]["stockQuantity"] == 28
    assert api.products["1"]["salePrice"] == 19900


def test_unknown_option_is_reported_not_written():
    supplier = MockSupplier(items={"X": SupplierItem("X", True, 1, cost=12480)})
    api = _pillow_api(1, 0, 0)
    report = sync_inventory(api, supplier, Settings(), [{"origin_product_no": "1", "sku": "X", "option_name": "블랙"}],
                            dry_run=True)
    assert report["ok"] is False
    assert report["planned"][0]["changes"][0]["error"]


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
    for k in ("SMARTSTORE_SMTP_HOST", "SMARTSTORE_NOTIFY_TO"):
        monkeypatch.delenv(k, raising=False)
    results = run(["all", "--mock", "--apply", "--notify"])
    assert results["sync-orders"]["ordered"] == ["2026092900001", "2026092900003"]
    assert results["sync-tracking"]["shipped"] == ["2026092900001", "2026092900003"]
    assert results["sync-inventory"]["restocked"] == ["1001 그레이"]
    assert len(results["draft-cs"]["drafted"]) == 2
    assert results["notified"] is False  # SMTP not configured -> printed only


def test_notify_summary():
    assert build_summary({"sync-orders": {"dry_run": False, "ordered": [], "failed": []}}) is None
    text = build_summary({
        "sync-orders": {"dry_run": False, "ordered": ["1"], "failed": [{"product_order_id": "2", "reason": "품절"}]},
        "sync-inventory": {"restocked": ["1001 그레이"], "sold_out": [], "planned": []},
    })
    assert "신규 주문 1건" in text and "직접 처리" in text and "재입고: 1001 그레이" in text
