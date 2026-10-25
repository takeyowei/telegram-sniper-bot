#!/usr/bin/env python3
"""demo.py - Offline demo of one full paper-trading session.

No token, no network, no real funds: replays a scripted channel call
through the real parser, SIMULATED checks and paper trader, then prints
every receipt and the final P&L report.

Run:  python demo.py
"""

from __future__ import annotations

from call_parser import parse_call
from paper_trader import PaperMarket, PaperTrader
from token_checks import simulated_checks

# Fixed demo mint (fake, base58-looking) chosen so the SIMULATED checks
# PASS; verified by running token_checks.simulated_checks on it.
DEMO_MINT = "Moon7111111111111111111111111111111111111111"
DEMO_MESSAGE = (
    "🚀 NEW CALL $MOON\n"
    f"CA: {DEMO_MINT}\n"
    "buy 1.5 SOL"
)


def main() -> None:
    print("=== TELEGRAM SNIPER BOT - PAPER DEMO (offline, no real funds) ===")
    print(f"\n[Channel post]\n{DEMO_MESSAGE}")

    call = parse_call(DEMO_MESSAGE)
    print(f"\nParsed call: mint={call.mint} symbol={call.symbol} "
          f"chain={call.chain} size={call.amount_sol} SOL")

    checks = simulated_checks(call.mint, call.symbol)
    print(f"\n{checks.format()}")
    assert checks.verdict == "PASS", f"demo mint must PASS, got {checks.verdict}"

    market = PaperMarket(seed=42)
    trader = PaperTrader(market, balance=100.0)

    receipt = trader.buy(call.mint, call.symbol, call.amount_sol)
    print(f"\n{receipt.format()}")

    for step in range(1, 11):
        price = market.tick(call.mint)
        print(f"  tick {step:2d}: price {price:.8f} SOL")
    print(f"\nAfter 10 ticks: {market.price(call.mint):.8f} SOL "
          f"(entry was {receipt.price:.8f} SOL)")

    sell = trader.sell(call.mint)
    print(f"\n{sell.format()}")
    print(f"\n{trader.pnl_report()}")
    print("\n=== END DEMO - everything above was paper, nothing real moved ===")


if __name__ == "__main__":
    main()
