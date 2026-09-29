"""Pricing rules for dropshipped products (pure functions, easy to test)."""
from __future__ import annotations

import math


def sale_price(cost: int, shipping_fee: int, fee_rate: float, target_margin: float, round_to: int = 100) -> int:
    """Price so that (price - fees - cost - shipping) / price == target_margin, rounded up.

    price = (cost + shipping) / (1 - fee_rate - target_margin)
    """
    denom = 1 - fee_rate - target_margin
    if denom <= 0:
        raise ValueError("fee_rate + target_margin must be < 1")
    raw = (cost + shipping_fee) / denom
    return int(math.ceil(raw / round_to) * round_to)


def margin_rate(price: int, cost: int, shipping_fee: int, fee_rate: float) -> float:
    if price <= 0:
        return float("-inf")
    return (price * (1 - fee_rate) - cost - shipping_fee) / price


def is_sellable(price: int, cost: int, shipping_fee: int, fee_rate: float, min_margin: float) -> bool:
    return margin_rate(price, cost, shipping_fee, fee_rate) >= min_margin
