"""Receiver contract vs the delivery_contract vector, plus drain and budget rules."""

import json
from pathlib import Path

import pytest

from cosmos77_cop.net.receiver import (
    ABSORB,
    APPLY,
    BUFFER,
    DISCARD,
    EQUIVOCATION,
    VIOLATION,
    BudgetError,
    Receiver,
    reconcile_budgets,
)

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "vectors" / "delivery_contract.json").read_text()
)


def from_fixture_state(state: dict) -> Receiver:
    return Receiver(
        window=state["window"],
        next_step=state["next"],
        played={int(k): v for k, v in state["played"].items()},
    )


@pytest.mark.parametrize("case", FIXTURE["arrivals"], ids=lambda c: c["note"][:40])
def test_delivery_contract_decision_table(case):
    r = from_fixture_state(FIXTURE["state"])
    assert r.decide(case["arrival"]["step"], case["arrival"]["commit"]) == case["decision"]


def test_window_zero_row_from_fixture():
    row = FIXTURE["no_reorder_window"]
    r = from_fixture_state(row["state"])
    assert r.decide(row["arrival"]["step"], row["arrival"]["commit"]) == row["decision"]


def test_all_six_decisions_exist():
    assert {APPLY, ABSORB, EQUIVOCATION, BUFFER, VIOLATION, DISCARD} == {
        c["decision"] for c in FIXTURE["arrivals"]
    }


def test_ingest_applies_and_drains_in_step_order():
    r = Receiver(window=4)
    assert r.ingest({"step": 2, "commit": "c2"}) == []
    assert r.ingest({"step": 3, "commit": "c3"}) == []
    applied = r.ingest({"step": 1, "commit": "c1"})
    assert [m["step"] for m in applied] == [1, 2, 3]
    assert r.next_step == 4
    assert r.played == {1: "c1", 2: "c2", 3: "c3"}


def test_ingest_duplicate_absorbs_and_equivocation_stays_loud():
    r = Receiver(window=4)
    r.ingest({"step": 1, "commit": "c1"})
    assert r.ingest({"step": 1, "commit": "c1"}) == []
    assert r.equivocations == []
    r.ingest({"step": 1, "commit": "cX"})
    assert r.equivocations == [(1, "c1", "cX")]


def test_ingest_flood_past_window_is_violation():
    r = Receiver(window=2)
    r.ingest({"step": 99, "commit": "c99"})
    assert r.violations == [99]
    assert r.next_step == 1


def test_budget_reconciliation_matrix():
    good = {
        "watchdog_s": 60.0,
        "poll_s": 0.05,
        "connect_timeout_s": 10.0,
        "turn_timeout_s": 30.0,
        "reorder_window": 4,
    }
    reconcile_budgets(**good)
    for key, bad in [
        ("watchdog_s", 0.0),
        ("poll_s", 61.0),
        ("connect_timeout_s", 31.0),
        ("reorder_window", 0),
    ]:
        with pytest.raises(BudgetError):
            reconcile_budgets(**{**good, key: bad})
