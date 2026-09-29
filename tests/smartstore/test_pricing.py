import pytest

from smartstore.pricing import is_sellable, margin_rate, sale_price


def test_sale_price_hits_target_margin():
    price = sale_price(8000, 3000, fee_rate=0.0563, target_margin=0.15, round_to=100)
    assert price % 100 == 0
    assert margin_rate(price, 8000, 3000, 0.0563) >= 0.15
    # rounding up should never add more than one rounding step
    assert sale_price(8000, 3000, 0.0563, 0.15, round_to=1) > price - 100


def test_min_margin_boundary():
    assert is_sellable(10000, 6000, 3000, 0.05, min_margin=0.05)      # exactly 5%
    assert not is_sellable(10000, 6100, 3000, 0.05, min_margin=0.05)  # 4%


def test_invalid_rates():
    with pytest.raises(ValueError):
        sale_price(1000, 0, fee_rate=0.5, target_margin=0.5)
