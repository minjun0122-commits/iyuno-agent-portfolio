"""CLI entry point, meant to be run from cron.

    python -m smartstore.jobs sync-orders            # dry-run (default): prints the plan only
    python -m smartstore.jobs sync-orders --apply    # actually confirm + purchase
    python -m smartstore.jobs sync-tracking --apply
    python -m smartstore.jobs sync-inventory --apply
    python -m smartstore.jobs draft-cs [--apply [--post]]
    python -m smartstore.jobs all --mock             # full pipeline on sample data, no credentials needed

Add --notify to email a summary when something needs attention (see smartstore/notify.py).
"""
from __future__ import annotations

import argparse
import json
import sys

from smartstore.config import Settings
from smartstore.cs import QnaAPI, draft_cs
from smartstore.orders import OrderAPI, OrderSync
from smartstore.products import ProductAPI, load_product_map, sync_inventory
from smartstore.store import Store

COMMANDS = ("sync-orders", "sync-tracking", "sync-inventory", "draft-cs", "all")


def _build(args, settings: Settings):
    if args.mock:
        from smartstore.fakes import demo_fixtures

        supplier, orders, products, product_map, qna = demo_fixtures()
        return supplier, orders, products, product_map, qna, Store(":memory:")

    from smartstore.client import CommerceClient
    from smartstore.suppliers.csv_supplier import CSVSupplier

    settings.require_credentials()
    client = CommerceClient(settings)
    supplier = CSVSupplier(settings.supplier_inventory_csv, settings.supplier_outbox_csv, settings.supplier_tracking_csv)
    return (supplier, OrderAPI(client), ProductAPI(client), load_product_map(settings.product_map_csv),
            QnaAPI(client), Store(settings.db_path))


def run(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(prog="smartstore.jobs")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--apply", action="store_true", help="perform writes (default is dry-run)")
    parser.add_argument("--post", action="store_true", help="draft-cs: also post answers (requires --apply)")
    parser.add_argument("--mock", action="store_true", help="use in-memory sample data instead of the real API")
    parser.add_argument("--notify", action="store_true", help="email a summary if anything needs attention")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    supplier, order_api, product_api, product_map, qna_api, store = _build(args, settings)
    dry_run = not args.apply
    sync = OrderSync(order_api, supplier, store, dry_run=dry_run)

    results: dict = {}
    if args.command in ("sync-orders", "all"):
        results["sync-orders"] = sync.sync_orders()
    if args.command == "all" and args.mock:
        supplier.ship_all()  # simulate the supplier shipping so the tracking step has data
    if args.command in ("sync-tracking", "all"):
        results["sync-tracking"] = sync.sync_tracking()
    if args.command in ("sync-inventory", "all"):
        results["sync-inventory"] = sync_inventory(product_api, supplier, settings, product_map, dry_run=dry_run)
    if args.command in ("draft-cs", "all"):
        results["draft-cs"] = draft_cs(qna_api, store, settings.cs_model, post=args.post, dry_run=dry_run)
    if args.notify:
        from smartstore.notify import build_summary, send

        summary = build_summary(results)
        results["notified"] = bool(summary) and send(summary)
    return results


def main() -> int:
    results = run()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    failed = sum(len(r.get("failed", [])) for r in results.values() if isinstance(r, dict))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
