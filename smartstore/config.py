"""Runtime settings, read from environment variables only (never hard-code keys)."""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.commerce.naver.com"


@dataclass
class Settings:
    client_id: str = ""
    client_secret: str = ""
    base_url: str = DEFAULT_BASE_URL
    db_path: str = "smartstore.db"
    # Naver Pay order-management fee + Naver Shopping sales-linked fee.
    # Conservative default (3.63% + 2%); check your seller center for the actual rates.
    fee_rate: float = 0.0563
    target_margin: float = 0.20
    min_margin: float = 0.05
    price_round_to: int = 100
    # Supplier (CSV mode): inventory sheet in, bulk-order sheet out, tracking sheet in.
    supplier_inventory_csv: str = "data/smartstore/supplier_inventory.csv"
    supplier_outbox_csv: str = "data/smartstore/supplier_orders_outbox.csv"
    supplier_tracking_csv: str = "data/smartstore/supplier_tracking.csv"
    product_map_csv: str = "data/smartstore/product_map.csv"
    cs_model: str = "claude-sonnet-5-5"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        base = cls()
        return cls(
            client_id=env("NAVER_COMMERCE_CLIENT_ID", ""),
            client_secret=env("NAVER_COMMERCE_CLIENT_SECRET", ""),
            base_url=env("NAVER_COMMERCE_BASE_URL", base.base_url),
            db_path=env("SMARTSTORE_DB", base.db_path),
            fee_rate=float(env("SMARTSTORE_FEE_RATE", base.fee_rate)),
            target_margin=float(env("SMARTSTORE_TARGET_MARGIN", base.target_margin)),
            min_margin=float(env("SMARTSTORE_MIN_MARGIN", base.min_margin)),
            price_round_to=int(env("SMARTSTORE_PRICE_ROUND_TO", base.price_round_to)),
            supplier_inventory_csv=env("SUPPLIER_INVENTORY_CSV", base.supplier_inventory_csv),
            supplier_outbox_csv=env("SUPPLIER_OUTBOX_CSV", base.supplier_outbox_csv),
            supplier_tracking_csv=env("SUPPLIER_TRACKING_CSV", base.supplier_tracking_csv),
            product_map_csv=env("SMARTSTORE_PRODUCT_MAP_CSV", base.product_map_csv),
            cs_model=env("SMARTSTORE_CS_MODEL", base.cs_model),
        )

    def require_credentials(self) -> None:
        if not (self.client_id and self.client_secret):
            raise RuntimeError(
                "NAVER_COMMERCE_CLIENT_ID / NAVER_COMMERCE_CLIENT_SECRET are not set. "
                "Use --mock to try the pipeline without real credentials."
            )
