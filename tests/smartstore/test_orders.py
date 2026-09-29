from smartstore.fakes import FakeOrderAPI, make_order
from smartstore.orders import OrderSync
from smartstore.store import Store
from smartstore.suppliers.base import SupplierItem
from smartstore.suppliers.mock import MockSupplier


def _supplier(**kw):
    return MockSupplier(items={
        "A": SupplierItem("A", True, 10, cost=5000),
        "B": SupplierItem("B", True, 0, cost=5000),  # out of stock
    }, **kw)


def test_dry_run_writes_nothing():
    api = FakeOrderAPI([make_order("1", "A"), make_order("2", "B")])
    store, supplier = Store(), _supplier()
    report = OrderSync(api, supplier, store, dry_run=True).sync_orders()
    assert [p["product_order_id"] for p in report["planned"]] == ["1"]
    assert report["failed"][0]["product_order_id"] == "2"
    assert api.confirmed == [] and supplier.placed == []
    assert store.get_order("1") is None and store.get_order("2") is None


def test_full_flow_new_to_shipped():
    api = FakeOrderAPI([make_order("1", "A", 2), make_order("2", "B"), make_order("3", "A", status="CANCELED")])
    store, supplier = Store(), _supplier()
    sync = OrderSync(api, supplier, store, dry_run=False)

    report = sync.sync_orders()
    assert report["ordered"] == ["1"]
    assert api.confirmed == ["1"]
    assert store.get_order("1")["status"] == "ORDERED"
    assert store.get_order("2")["status"] == "FAILED"   # out of stock -> not confirmed
    assert store.get_order("3") is None                  # cancelled -> ignored
    assert supplier.placed[0].recipient["name"] == "홍길동"
    assert supplier.placed[0].quantity == 2

    assert sync.sync_tracking()["shipped"] == []  # supplier hasn't shipped yet
    supplier.ship_all()
    report = sync.sync_tracking()
    assert report["shipped"] == ["1"]
    assert api.dispatched[0]["deliveryCompanyCode"] == "CJGLS"
    assert store.get_order("1")["status"] == "SHIPPED"


def test_rerun_is_idempotent():
    api = FakeOrderAPI([make_order("1", "A")])
    store, supplier = Store(), _supplier()
    sync = OrderSync(api, supplier, store, dry_run=False)
    sync.sync_orders()
    sync.sync_orders()
    assert api.confirmed == ["1"]
    assert len(supplier.placed) == 1


def test_confirm_rejected_marks_failed():
    api = FakeOrderAPI([make_order("1", "A")], reject_confirm={"1"})
    store, supplier = Store(), _supplier()
    OrderSync(api, supplier, store, dry_run=False).sync_orders()
    assert store.get_order("1")["status"] == "FAILED"
    assert supplier.placed == []


def test_purchase_failure_marks_failed():
    api = FakeOrderAPI([make_order("1", "A")])
    store, supplier = Store(), _supplier(fail_skus={"A"})
    report = OrderSync(api, supplier, store, dry_run=False).sync_orders()
    assert store.get_order("1")["status"] == "FAILED"
    assert "purchase failed" in store.get_order("1")["reason"]
    assert report["failed"]


def test_confirmed_but_not_purchased_is_resumed():
    api = FakeOrderAPI([make_order("1", "A")])
    store, supplier = Store(), _supplier()
    store.upsert_order("1", "CONFIRMED", sku="A", quantity=1)  # crash after confirm on a previous run
    report = OrderSync(api, supplier, store, dry_run=False).sync_orders()
    assert report["ordered"] == ["1"]
    assert api.confirmed == []  # not confirmed twice


def test_dispatch_rejected_stays_ordered_for_retry():
    api = FakeOrderAPI([make_order("1", "A")], reject_dispatch={"1"})
    store, supplier = Store(), _supplier()
    sync = OrderSync(api, supplier, store, dry_run=False)
    sync.sync_orders()
    supplier.ship_all()
    sync.sync_tracking()
    row = store.get_order("1")
    assert row["status"] == "ORDERED" and "dispatch failed" in row["reason"]
