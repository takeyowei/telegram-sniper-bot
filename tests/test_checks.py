"""Tests for the SIMULATED token checks (deterministic by mint hash).
Run with: python -m pytest tests/ -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from token_checks import simulated_checks  # noqa: E402

# Fake base58-looking mints, one per verdict branch (found by scanning).
PASS_MINT = "Test2211111111111111111111111111111111111111"
WARN_MINT = "Test011111111111111111111111111111111111111"
BLOCK_MINT = "Test111111111111111111111111111111111111111"


def test_verdict_branches():
    assert simulated_checks(PASS_MINT, "T").verdict == "PASS"
    assert simulated_checks(WARN_MINT, "T").verdict == "WARN"
    assert simulated_checks(BLOCK_MINT, "T").verdict == "BLOCK"


def test_every_result_is_flagged_simulated():
    result = simulated_checks(PASS_MINT, "T")
    assert result.simulated is True
    assert "simulated" in result.format().lower()


def test_checks_are_deterministic():
    first = simulated_checks(PASS_MINT, "T")
    second = simulated_checks(PASS_MINT, "T")
    assert first == second
