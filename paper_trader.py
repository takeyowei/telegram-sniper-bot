"""paper_trader.py - Simulated market, wallet and order execution.

PAPER TRADING ONLY. There is no wallet, no private key, no RPC endpoint
and no real-money code path anywhere in this module — balances are plain
floats in "paper SOL" and prices come from a seeded random walk, so every
run is reproducible and no funds can move.

Market model
------------
- Each mint gets a deterministic base price (SOL per token) derived from
  its sha256 hash, so the same mint always starts at the same price.
- ``tick()`` advances the price with a seeded Gaussian walk (2% per-tick
  volatility). Same seed + same tick sequence = same prices, which is
  what makes the tests deterministic.

Costs (all simulated)
---------------------
- Fee: 0.25% of the traded size, both sides.
- Slippage: 0.1% + 0.05% per paper SOL traded, capped at 2%.

Latency fields
--------------
- ``processing_ms`` is REALLY measured: wall-clock time of the local
  simulated execution path (perf_counter around it).
- ``modeled_confirm_ms`` is a MODELLED chain-confirmation delay derived
  deterministically from the mint hash. It is labelled "modelled" in
  every receipt because no chain is ever contacted.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field

PAPER_SOL_START = 100.0
FEE_PCT = 0.25
TICK_VOLATILITY = 0.02


def _hash_int(mint: str) -> int:
    return int(hashlib.sha256(mint.encode()).hexdigest()[:8], 16)


def slippage_pct(amount_sol: float) -> float:
    """Simulated slippage: grows with size, capped at 2%."""
    return min(2.0, 0.1 + amount_sol * 0.05)


class PaperMarket:
    """Seeded random-walk price feed. No network, no real prices."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.prices: dict[str, float] = {}

    def base_price(self, mint: str) -> float:
        """Deterministic starting price in SOL per token."""
        return 1e-6 * (1 + (_hash_int(mint) % 1000) / 100.0)

    def price(self, mint: str) -> float:
        return self.prices.setdefault(mint, self.base_price(mint))

    def tick(self, mint: str, steps: int = 1) -> float:
        """Advance the price ``steps`` ticks; returns the new price."""
        price = self.price(mint)
        for _ in range(steps):
            price = max(price * (1 + self.rng.gauss(0, TICK_VOLATILITY)), 1e-12)
        self.prices[mint] = price
        return price


@dataclass
class Position:
    mint: str
    symbol: str | None
    qty: float
    entry_price: float  # average SOL per token, slippage-adjusted
    cost_sol: float     # paper SOL spent (including fees) for this qty


@dataclass
class OrderReceipt:
    side: str  # "BUY" | "SELL"
    mint: str
    symbol: str | None
    amount_sol: float
    price: float
    qty: float
    fee_sol: float
    slippage_pct: float
    processing_ms: float       # really measured, local execution only
    modeled_confirm_ms: int    # MODELLED delay, no chain contacted
    realized_pnl_sol: float = 0.0
    note: str = "PAPER ONLY - no real funds"

    def format(self) -> str:
        lines = [
            f"{self.side} {self.symbol or self.mint} (PAPER)",
            f"  size: {self.amount_sol:.4f} paper SOL @ {self.price:.8f} SOL",
            f"  qty: {self.qty:.2f} | fee: {self.fee_sol:.4f} | "
            f"slippage: {self.slippage_pct:.2f}%",
            f"  latency: {self.processing_ms:.2f} ms processing "
            f"(measured) + {self.modeled_confirm_ms} ms confirm (modelled)",
        ]
        if self.side == "SELL":
            lines.append(f"  realized P&L: {self.realized_pnl_sol:+.4f} paper SOL")
        return "\n".join(lines)


@dataclass
class PaperTrader:
    """Paper wallet + positions. Balances are floats, never real money."""

    market: PaperMarket
    balance: float = PAPER_SOL_START
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    history: list[OrderReceipt] = field(default_factory=list)

    def buy(self, mint: str, symbol: str | None, amount_sol: float) -> OrderReceipt:
        if amount_sol <= 0:
            raise ValueError("buy size must be positive")
        if amount_sol > self.balance:
            raise ValueError("insufficient paper balance")
        started = time.perf_counter()
        price = self.market.price(mint)
        slip = slippage_pct(amount_sol)
        fee = amount_sol * FEE_PCT / 100
        eff_price = price * (1 + slip / 100)
        qty = (amount_sol - fee) / eff_price
        self.balance -= amount_sol
        existing = self.positions.get(mint)
        if existing:
            total_qty = existing.qty + qty
            existing.entry_price = (
                existing.entry_price * existing.qty + eff_price * qty
            ) / total_qty
            existing.qty = total_qty
            existing.cost_sol += amount_sol
        else:
            self.positions[mint] = Position(
                mint=mint, symbol=symbol, qty=qty,
                entry_price=eff_price, cost_sol=amount_sol,
            )
        receipt = OrderReceipt(
            side="BUY", mint=mint, symbol=symbol, amount_sol=amount_sol,
            price=eff_price, qty=qty, fee_sol=fee, slippage_pct=slip,
            processing_ms=(time.perf_counter() - started) * 1000,
            modeled_confirm_ms=400 + (_hash_int(mint) % 1200),
        )
        self.history.append(receipt)
        return receipt

    def sell(self, mint: str, pct: float = 100.0) -> OrderReceipt:
        position = self.positions.get(mint)
        if position is None:
            raise ValueError("no paper position for this mint")
        if not 0 < pct <= 100:
            raise ValueError("sell pct must be in (0, 100]")
        started = time.perf_counter()
        qty = position.qty * pct / 100
        cost_share = position.cost_sol * pct / 100
        price = self.market.price(mint)
        slip = slippage_pct(cost_share)
        eff_price = price * (1 - slip / 100)
        proceeds = qty * eff_price
        fee = proceeds * FEE_PCT / 100
        net = proceeds - fee
        realized = net - cost_share
        self.balance += net
        self.realized_pnl += realized
        position.qty -= qty
        position.cost_sol -= cost_share
        if position.qty <= 1e-9:
            del self.positions[mint]
        receipt = OrderReceipt(
            side="SELL", mint=mint, symbol=position.symbol,
            amount_sol=net, price=eff_price, qty=qty, fee_sol=fee,
            slippage_pct=slip,
            processing_ms=(time.perf_counter() - started) * 1000,
            modeled_confirm_ms=400 + (_hash_int(mint) % 1200),
            realized_pnl_sol=realized,
        )
        self.history.append(receipt)
        return receipt

    def pnl_report(self) -> str:
        """Per-position unrealised P&L at current paper prices + totals."""
        lines = ["PAPER P&L REPORT (no real funds)"]
        total_unrealised = 0.0
        for position in self.positions.values():
            current = self.market.price(position.mint)
            value = position.qty * current
            unrealised = value - position.cost_sol
            total_unrealised += unrealised
            lines.append(
                f"  {position.symbol or position.mint}: "
                f"{position.qty:.2f} tokens, entry {position.entry_price:.8f} "
                f"-> now {current:.8f} SOL, unrealised "
                f"{unrealised:+.4f} paper SOL"
            )
        lines.append(f"  realised: {self.realized_pnl:+.4f} paper SOL")
        lines.append(f"  unrealised: {total_unrealised:+.4f} paper SOL")
        lines.append(
            f"  total: {self.realized_pnl + total_unrealised:+.4f} paper SOL"
        )
        lines.append(f"  paper balance: {self.balance:.4f} paper SOL")
        return "\n".join(lines)
