"""token_checks.py - SIMULATED honeypot / rug checks.

READ THIS FIRST: every value in this module is SIMULATED. Nothing here
touches a chain, a RPC node, or a real token contract. The numbers are
derived deterministically from the sha256 hash of the mint string, so
the same mint always yields the same verdict and tests stay stable.

Why simulated? A real honeypot check needs a forked-state sell
simulation against a live chain (or a paid API) — that is out of scope
for a portfolio demo and would require real infrastructure. This module
exists to show the *pipeline shape* a real sniper bot needs:

    call -> simulated checks -> PASS / WARN / BLOCK -> paper trade

Verdict rules (on simulated values):

- BLOCK: simulated sell fails, or simulated sell tax > 50%.
- WARN:  simulated sell tax > 20%, buy tax > 10%, or low liquidity.
- PASS:  otherwise.

A real deployment MUST replace ``simulated_checks`` with a real
simulation before touching any real funds. This repo never will: it
contains no real-money code path by design.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class CheckResult:
    mint: str
    symbol: str | None
    buy_tax_pct: float       # SIMULATED
    sell_tax_pct: float      # SIMULATED
    simulated_sell_ok: bool  # SIMULATED
    low_liquidity: bool      # SIMULATED
    verdict: str             # "PASS" | "WARN" | "BLOCK"
    simulated: bool = True

    def format(self) -> str:
        return (
            f"SIMULATED checks for {self.symbol or self.mint}:\n"
            f"  buy tax: {self.buy_tax_pct:.1f}% (simulated)\n"
            f"  sell tax: {self.sell_tax_pct:.1f}% (simulated)\n"
            f"  simulated sell test: "
            f"{'OK' if self.simulated_sell_ok else 'FAILED'} (simulated)\n"
            f"  liquidity: {'LOW (simulated)' if self.low_liquidity else 'OK (simulated)'}\n"
            f"  verdict: {self.verdict}"
        )


def simulated_checks(mint: str, symbol: str | None = None) -> CheckResult:
    """Deterministic SIMULATED checks for a mint. No chain is contacted."""
    digest = int(hashlib.sha256(mint.encode()).hexdigest()[:8], 16)
    buy_tax = (digest % 150) / 10.0    # 0.0 - 14.9 (simulated)
    sell_tax = (digest % 600) / 10.0   # 0.0 - 59.9 (simulated)
    sell_ok = (digest % 7) != 0        # simulated sell test
    low_liq = (digest % 5) == 0        # simulated liquidity flag
    if (not sell_ok) or sell_tax > 50:
        verdict = "BLOCK"
    elif sell_tax > 20 or buy_tax > 10 or low_liq:
        verdict = "WARN"
    else:
        verdict = "PASS"
    return CheckResult(
        mint=mint, symbol=symbol, buy_tax_pct=buy_tax,
        sell_tax_pct=sell_tax, simulated_sell_ok=sell_ok,
        low_liquidity=low_liq, verdict=verdict,
    )
