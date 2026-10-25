"""Tests for the paper market and trader (no network, seeded prices).
Run with: python -m pytest tests/ -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paper_trader import (  # noqa: E402
    FEE_PCT,
    PaperMarket,
    PaperTrader,
    slippage_pct,
)

MINT = "Moon7111111111111111111111111111111111111111"


@pytest.fixture()
def trader():
    return PaperTrader(PaperMarket(seed=42), balance=100.0)


def test_buy_creates_position_and_charges_fee(trader):
    receipt = trader.buy(MINT, "MOON", 10.0)
    assert trader.balance == pytest.approx(90.0)
    position = trader.positions[MINT]
    assert position.qty == pytest.approx(receipt.qty)
    assert receipt.fee_sol == pytest.approx(10.0 * FEE_PCT / 100)
    assert receipt.note.startswith("PAPER ONLY")
    assert receipt.processing_ms >= 0
    assert 400 <= receipt.modeled_confirm_ms < 1600


def test_buy_more_than_balance_raises(trader):
    with pytest.raises(ValueError, match="insufficient paper balance"):
        trader.buy(MINT, "MOON", 101.0)


def test_sell_full_closes_position_and_books_realized(trader):
    trader.buy(MINT, "MOON", 10.0)
    trader.market.tick(MINT, steps=5)
    receipt = trader.sell(MINT)
    assert MINT not in trader.positions
    assert receipt.side == "SELL"
    assert trader.realized_pnl == pytest.approx(receipt.realized_pnl_sol)


def test_sell_partial_keeps_remainder(trader):
    trader.buy(MINT, "MOON", 10.0)
    qty_before = trader.positions[MINT].qty
    trader.sell(MINT, pct=50.0)
    assert trader.positions[MINT].qty == pytest.approx(qty_before / 2)


def test_sell_without_position_raises(trader):
    with pytest.raises(ValueError, match="no paper position"):
        trader.sell(MINT)


def test_market_is_deterministic_for_same_seed():
    first = PaperMarket(seed=7)
    second = PaperMarket(seed=7)
    assert first.price(MINT) == second.price(MINT)
    assert first.tick(MINT, steps=10) == second.tick(MINT, steps=10)


def test_market_moves_with_ticks():
    market = PaperMarket(seed=42)
    before = market.price(MINT)
    after = market.tick(MINT, steps=10)
    assert after != before
    assert after > 0


def test_slippage_grows_and_caps():
    assert slippage_pct(1.0) == pytest.approx(0.15)
    assert slippage_pct(1000.0) == 2.0
