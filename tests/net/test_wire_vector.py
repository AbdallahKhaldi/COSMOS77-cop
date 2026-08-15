"""Our turn admission reproduces the kit vector's validation table, case by case."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosmos77_cop.net.wire import refuse_turn

VECTOR = json.loads((Path(__file__).resolve().parents[1] / "vectors"
                     / "turn_message.json").read_text(encoding="utf-8"))
CASES = VECTOR["validation"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["note"][:48])
def test_vector_validation_case(case):
    reason = refuse_turn(case["message"])
    if case["verdict"] == "accept":
        assert reason is None, f"vector says accept, we refused: {reason}"
    else:
        assert reason is not None, f"vector says refuse ({case['verdict']}), we accepted"


def test_our_own_outbound_turn_passes_our_own_gate():
    """We must never send what we would refuse (the fairness inverse)."""
    ours = {"step": 1, "sender": "police", "hint": "", "smell_grid": {"3,3": 0.9},
            "commit": "a" * 64, "timestamp": "2026-08-15T00:00:00+00:00",
            "barrier_placed": None, "capture_claim": None}
    assert refuse_turn(ours) is None
