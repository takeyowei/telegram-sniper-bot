"""call_parser.py - Parse token calls from Telegram channel messages.

Pure functions, no network. A "call" is a message that names a token and
optionally a buy size, e.g.::

    🚀 NEW CALL $MOON
    CA: Moon111111111111111111111111111111111111111
    buy 1.5 SOL

Supported token references:

- EVM contract: ``0x`` + 40 hex chars.
- SOL mint: a 32-44 char base58 string, preferably after ``CA:`` /
  ``contract`` / ``mint`` / ``address``; a standalone base58 token also
  matches.
- ``$SYMBOL`` only: parsed, but the bot will NOT trade on it — simulated
  honeypot/rug checks need a contract address (see token_checks.py and
  bot.py), so a symbol-only call is answered with a request for the CA.

Buy size: ``buy 1.5 SOL``, ``ape 0.5 SOL``, ``amount: 2 SOL`` or any
``<number> SOL`` in the message. Missing size -> the bot's default paper
size applies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EVM_RE = re.compile(r"0x[a-fA-F0-9]{40}")
# Base58 without 0, O, I, l.
SOL_KEYWORD_RE = re.compile(
    r"(?:CA|contract|mint|address)\s*[:=]?\s*([1-9A-HJ-NP-Za-km-z]{32,44})",
    re.IGNORECASE,
)
SOL_STANDALONE_RE = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
SYMBOL_RE = re.compile(r"\$([A-Za-z]{2,12})\b")
AMOUNT_RE = re.compile(
    r"(?:buy|ape|amount|in)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*SOL\b", re.IGNORECASE
)
AMOUNT_FALLBACK_RE = re.compile(r"(\d+(?:\.\d+)?)\s*SOL\b", re.IGNORECASE)


@dataclass
class Call:
    """One parsed token call. ``mint`` is None for symbol-only calls."""

    mint: str | None
    symbol: str | None
    chain: str | None  # "SOL" | "EVM" | None
    amount_sol: float | None
    raw: str


def parse_call(text: str) -> Call | None:
    """Parse a channel message into a Call, or None if it is not a call."""
    if not text or not text.strip():
        return None

    evm = EVM_RE.search(text)
    if evm:
        mint, chain = evm.group(0), "EVM"
    else:
        keyword = SOL_KEYWORD_RE.search(text)
        if keyword:
            mint, chain = keyword.group(1), "SOL"
        else:
            mint, chain = None, None
            for match in SOL_STANDALONE_RE.finditer(text):
                mint, chain = match.group(0), "SOL"
                break

    symbol_match = SYMBOL_RE.search(text)
    symbol = symbol_match.group(1).upper() if symbol_match else None

    amount_match = AMOUNT_RE.search(text) or AMOUNT_FALLBACK_RE.search(text)
    amount_sol = float(amount_match.group(1)) if amount_match else None

    if mint is None and symbol is None:
        return None
    return Call(mint=mint, symbol=symbol, chain=chain,
                amount_sol=amount_sol, raw=text)
