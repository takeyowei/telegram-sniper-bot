#!/usr/bin/env python3
"""bot.py - A Telegram sniper bot demo that trades PAPER ONLY.

Listens for token calls posted in a channel (or sent to the bot), parses
the token + buy size, runs SIMULATED honeypot/rug checks, and executes
the trade on a simulated market with a paper wallet. No real wallet, no
private key, no RPC, no real-money code path exists in this repo.

Setup
-----
1. Create a bot with @BotFather on Telegram and copy its token.
2. cp .env.example .env  and paste the token into .env
3. pip install -r requirements.txt
4. python bot.py

Commands: /start /balance /positions /pnl /help
Channel posts: a token call (``$SYMBOL`` + contract/mint + ``buy X SOL``)
is parsed, SIMULATED-checked and paper-traded; BLOCK verdicts and
symbol-only calls (no contract to check) are skipped, never traded.
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from call_parser import parse_call
from paper_trader import PaperMarket, PaperTrader
from token_checks import simulated_checks

DEFAULT_PAPER_SIZE_SOL = 1.0
START_BALANCE_SOL = 100.0

log = logging.getLogger(__name__)


def _trader(context: ContextTypes.DEFAULT_TYPE) -> PaperTrader:
    return context.bot_data["trader"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Paper sniper bot demo (PAPER ONLY - no real funds).\n"
        "Post a token call with a contract/mint and a size, e.g.:\n"
        "$MOON\nCA: Moon7111111111111111111111111111111111111111\nbuy 1.5 SOL\n\n"
        "Commands: /balance /positions /pnl /help"
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    trader = _trader(context)
    await update.message.reply_text(
        f"Paper balance: {trader.balance:.4f} paper SOL\n"
        f"Open positions: {len(trader.positions)}"
    )


async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    trader = _trader(context)
    if not trader.positions:
        await update.message.reply_text("No open paper positions.")
        return
    lines = ["Open paper positions:"]
    for position in trader.positions.values():
        lines.append(
            f"  {position.symbol or position.mint}: {position.qty:.2f} tokens, "
            f"entry {position.entry_price:.8f} SOL, "
            f"cost {position.cost_sol:.4f} paper SOL"
        )
    await update.message.reply_text("\n".join(lines))


async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_trader(context).pnl_report())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - welcome\n"
        "/balance - paper SOL balance\n"
        "/positions - open paper positions\n"
        "/pnl - paper P&L report\n\n"
        "Or just post a token call: $SYMBOL + contract/mint + buy X SOL.\n"
        "Trades are PAPER ONLY. Checks are SIMULATED."
    )


async def handle_call(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle one channel/group message that may contain a token call."""
    text = update.message.text or ""
    call = parse_call(text)
    if call is None:
        return  # not a token call; ignore silently
    if call.mint is None:
        await update.message.reply_text(
            f"Call for ${call.symbol} has no contract address, so no "
            "SIMULATED checks can run - skipped, nothing traded. "
            "Post the CA/mint to trade it on paper."
        )
        return
    checks = simulated_checks(call.mint, call.symbol)
    if checks.verdict == "BLOCK":
        await update.message.reply_text(
            f"{checks.format()}\nBLOCKED - nothing traded (paper)."
        )
        return
    trader = _trader(context)
    size = call.amount_sol if call.amount_sol is not None else DEFAULT_PAPER_SIZE_SOL
    try:
        receipt = trader.buy(call.mint, call.symbol, size)
    except ValueError as exc:
        await update.message.reply_text(f"Paper trade failed: {exc}")
        return
    prefix = f"{checks.format()}\nVerdict {checks.verdict} - paper trade opened."
    if checks.verdict == "WARN":
        prefix += " (WARN: traded on paper anyway for the demo log.)"
    await update.message.reply_text(f"{prefix}\n{receipt.format()}")


def build_application(
    token: str, trader: PaperTrader, market: PaperMarket
) -> Application:
    """Build the python-telegram-bot Application (no network I/O).

    Environment note (this dev VM only, not a code issue): the VM routes
    traffic through an egress proxy and exports a NO_PROXY list with
    bracketed IPv6 entries that the installed httpx cannot parse, so
    building the Application crashes with InvalidURL unless the
    *_PROXY / NO_PROXY variables are unset first. On a normal machine
    these variables are absent and the build passes as-is.
    """
    app = Application.builder().token(token).build()
    app.bot_data["trader"] = trader
    app.bot_data["market"] = market
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("positions", positions))
    app.add_handler(CommandHandler("pnl", pnl))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_call)
    )
    return app


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print(
            "BOT_TOKEN is not set. Copy .env.example to .env and paste "
            "your @BotFather token there, then run: python bot.py"
        )
        return 1
    market = PaperMarket()
    trader = PaperTrader(market, balance=START_BALANCE_SOL)
    app = build_application(token, trader, market)
    print(
        f"Paper sniper bot running (PAPER ONLY, "
        f"starting balance {START_BALANCE_SOL} paper SOL). "
        "Post a token call to paper-trade it."
    )
    app.run_polling()
    return 0


if __name__ == "__main__":
    sys.exit(main())
