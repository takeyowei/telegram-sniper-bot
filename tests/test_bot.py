"""Tests for the bot wiring: offline Application build + no-token exit.
No Telegram network is used; building an Application performs no I/O.

Run with: python -m pytest tests/ -v
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bot  # noqa: E402
from paper_trader import PaperMarket, PaperTrader  # noqa: E402


@pytest.fixture(autouse=True)
def _no_proxy(monkeypatch):
    """Dev-VM quirk: bracketed IPv6 entries in NO_PROXY break httpx
    when python-telegram-bot builds its Application. Unset them here
    (same workaround as the offline build check in BUILD_LOG.md)."""
    for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(var, raising=False)


def test_application_builds_with_all_handlers():
    market = PaperMarket(seed=42)
    trader = PaperTrader(market)
    app = bot.build_application("123456:TEST", trader, market)
    handlers = app.handlers[0]
    # 5 commands (/start /balance /positions /pnl /help) + 1 call handler
    assert len(handlers) == 6
    assert app.bot_data["trader"] is trader


def test_main_exits_without_token(monkeypatch, capsys):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    assert bot.main() == 1
    assert "BOT_TOKEN is not set" in capsys.readouterr().out
