"""Tests for the call parser (no Telegram network needed).
Run with: python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from call_parser import parse_call  # noqa: E402

EVM = "0x" + "ab" * 20
SOL = "Moon7111111111111111111111111111111111111111"


def test_evm_contract_and_amount():
    call = parse_call(f"🚀 NEW CALL $PEPE\nContract: {EVM}\nbuy 2 SOL")
    assert call is not None
    assert call.mint == EVM
    assert call.chain == "EVM"
    assert call.symbol == "PEPE"
    assert call.amount_sol == 2.0


def test_sol_mint_after_ca_keyword():
    call = parse_call(f"$MOON\nCA: {SOL}\nbuy 1.5 SOL")
    assert call is not None
    assert call.mint == SOL
    assert call.chain == "SOL"
    assert call.amount_sol == 1.5


def test_sol_mint_standalone():
    call = parse_call(f"ape {SOL} 0.5 SOL")
    assert call is not None
    assert call.mint == SOL
    assert call.chain == "SOL"
    assert call.amount_sol == 0.5


def test_symbol_only_call_has_no_mint():
    call = parse_call("🚀 $DOGE to the moon, buy 1 SOL")
    assert call is not None
    assert call.mint is None
    assert call.symbol == "DOGE"
    assert call.amount_sol == 1.0


def test_amount_variants():
    assert parse_call(f"{SOL} amount: 3 SOL").amount_sol == 3.0
    assert parse_call(f"{SOL} in 0.25 SOL").amount_sol == 0.25
    assert parse_call(f"{SOL}").amount_sol is None


def test_garbage_is_not_a_call():
    assert parse_call("hello everyone, good morning") is None
    assert parse_call("") is None
    assert parse_call("   ") is None
