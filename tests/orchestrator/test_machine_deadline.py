"""State machine legality (rules 4-5) and the one-clock deadline rule (fixture rows)."""

import json
from pathlib import Path

import pytest

from cosmos77_cop.orchestrator import machine as sm
from cosmos77_cop.orchestrator.deadline import EXPIRED, WAITING, DeadlineClock
from cosmos77_cop.orchestrator.watchdog import Watchdog

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "vectors" / "delivery_contract.json").read_text()
)


def test_happy_loop_and_done():
    m = sm.StateMachine()
    for target in [sm.COMPUTING_MOVE, sm.COMMITTING, sm.AWAITING_REVEAL, sm.VERIFYING]:
        m.transition(target)
    m.transition(sm.COMPUTING_MOVE)
    for target in [sm.COMMITTING, sm.AWAITING_REVEAL, sm.VERIFYING, sm.DONE]:
        m.transition(target)
    assert m.absorbed


def test_every_illegal_transition_raises():
    states = [
        sm.WAITING_FOR_OPPONENT,
        sm.COMPUTING_MOVE,
        sm.COMMITTING,
        sm.AWAITING_REVEAL,
        sm.VERIFYING,
        sm.TECHNICAL_LOSS,
        sm.DONE,
    ]
    legal = {
        (sm.WAITING_FOR_OPPONENT, sm.COMPUTING_MOVE),
        (sm.COMPUTING_MOVE, sm.COMMITTING),
        (sm.COMMITTING, sm.AWAITING_REVEAL),
        (sm.AWAITING_REVEAL, sm.VERIFYING),
        (sm.VERIFYING, sm.COMPUTING_MOVE),
        (sm.VERIFYING, sm.DONE),
    }
    for src in states:
        for dst in states:
            m = sm.StateMachine()
            m.state = src
            absorbing = src in (sm.TECHNICAL_LOSS, sm.DONE)
            if (src, dst) in legal or (dst == sm.TECHNICAL_LOSS and not absorbing):
                m.transition(dst)
            else:
                with pytest.raises(sm.IllegalTransitionError):
                    m.transition(dst)


def test_technical_loss_absorbs():
    m = sm.StateMachine()
    m.transition(sm.TECHNICAL_LOSS)
    assert m.absorbed
    with pytest.raises(sm.IllegalTransitionError):
        m.transition(sm.COMPUTING_MOVE)


@pytest.mark.parametrize("row", FIXTURE["deadline_rule"], ids=lambda r: r["note"][:40])
def test_deadline_rows_from_fixture(row):
    clock = DeadlineClock(row["deadline_at"])
    verdict = clock.lap(row["now"], arrived=row["arrived"], tolerated=row["tolerated"])
    assert verdict == {"waiting": WAITING, "expired": EXPIRED}[row["decision"]]


def test_tolerated_traffic_never_renews():
    clock = DeadlineClock(100.0)
    for now in [10.0, 50.0, 99.0]:
        assert clock.lap(now, arrived=True, tolerated=True) == WAITING
    assert clock.lap(100.0, arrived=True, tolerated=True) == EXPIRED
    clock.rearm(200.0)
    assert clock.lap(150.0) == WAITING


def test_watchdog_fires_rescue_exactly_once():
    fired = []
    dog = Watchdog(60.0, rescue=lambda: fired.append(1))
    dog.beat(0.0)
    assert not dog.check(59.9)
    assert dog.check(60.0)
    assert dog.check(120.0)
    assert fired == [1]
