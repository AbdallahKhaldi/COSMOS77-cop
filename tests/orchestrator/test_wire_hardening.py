"""Hostile-wire hardening: barrier validation, claim-receipt answers, survival gating,
equivocation/violation surfacing (rules 15, 21-22, 46-47; kit delivery contract)."""

import json
from pathlib import Path
from unittest.mock import patch

from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.net.server import PeerInbox
from cosmos77_cop.orchestrator.gateway import Gateway
from cosmos77_cop.orchestrator.peerconf import PeerConfig
from cosmos77_cop.orchestrator.subreport import SubGameReport, audit_phase, observe_batch
from cosmos77_cop.orchestrator.turnactions import observe_turn
from cosmos77_cop.orchestrator.turnactions_thief import thief_act
from cosmos77_cop.orchestrator.turnstate import SideKit, fresh_state
from cosmos77_cop.protocol.sealing import commit

REPO = Path(__file__).resolve().parents[2]
CFG = from_dict(json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8")))


def wire(step, sender="police", **extra):
    return {
        "step": step, "sender": sender, "commit": f"c{step:02d}", "hint": "",
        "smell_grid": {}, "timestamp": "t", **extra,
    }


def state_kit(role):
    return fresh_state(CFG, role), SideKit.fresh(CFG, role, seed=7)


# --- A4: inbound barrier declarations are validated, never crash, never fabricate ---


def test_off_board_barrier_is_a_violation_not_a_crash():
    state, kit = state_kit("thief")
    observe_turn(state, kit, wire(1, barrier_placed=[9, 9]))
    assert state.board.barriers == set()
    assert any("off-board" in v for v in state.wire_violations)
    assert not state.over


def test_barrier_past_quota_is_refused():
    state, kit = state_kit("thief")
    cells = [[0, c] for c in range(7)] + [[6, c] for c in range(7)]
    for step, cell in enumerate(cells, start=1):
        observe_turn(state, kit, wire(step, barrier_placed=cell))
    assert len(state.board.barriers) == CFG.max_barriers == 14
    assert state.wire_violations == []
    observe_turn(state, kit, wire(15, barrier_placed=[5, 5]))
    assert len(state.board.barriers) == 14
    assert any("quota" in v for v in state.wire_violations)


def test_thief_sent_barrier_is_never_absorbed_by_the_cop_side():
    state, kit = state_kit("police")
    observe_turn(state, kit, wire(1, sender="thief", barrier_placed=[2, 2]))
    observe_turn(state, kit, wire(2, sender="police", barrier_placed=[2, 3]))
    assert state.board.barriers == set()
    assert len(state.wire_violations) == 2


def test_forged_box_cannot_capture_our_thief():
    state, kit = state_kit("thief")
    cells = [[0, c] for c in range(7)] + [[6, c] for c in range(7)]
    for step, cell in enumerate(cells, start=1):
        observe_turn(state, kit, wire(step, barrier_placed=cell))
    for step, cell in enumerate(([2, 3], [4, 3], [3, 2], [3, 4]), start=15):
        observe_turn(state, kit, wire(step, barrier_placed=cell))
    from cosmos77_cop.engine.capture import is_rule47_boxed

    assert not is_rule47_boxed(state.board, state.my_pos)
    assert len(state.wire_violations) == 4 and not state.over


def test_valid_rule46_barrier_on_our_cell_still_captures():
    state, kit = state_kit("thief")
    observe_turn(state, kit, wire(1, barrier_placed=[3, 3]))
    assert state.over and state.ending.result == "capture"
    assert state.ending.reason.startswith("rule_46")


def test_garbage_wire_input_is_swallowed_as_a_violation():
    state, kit = state_kit("thief")
    observe_batch(state, kit, object(), [wire(1, barrier_placed=["x", "y"])])
    assert any("unfoldable" in v for v in state.wire_violations)
    assert not state.over


# --- A5: survival win_claims are gated on the threshold ---


def test_premature_survival_claim_is_refused_as_a_violation():
    state, kit = state_kit("police")
    observe_turn(state, kit, wire(1, win_claim={"type": "survival"}))
    assert not state.over
    assert any("survival" in v for v in state.wire_violations)


def test_survival_claim_at_the_threshold_is_accepted():
    state, kit = state_kit("police")
    state.their_turns = CFG.survival_threshold - 1
    observe_turn(state, kit, wire(35, win_claim={"type": "survival"}))
    assert state.over and state.ending.result == "survival"


# --- A2: capture claims are answered against the position AT CLAIM RECEIPT ---


def test_true_claim_settles_on_a_terminal_stay_at_receipt_position():
    state, kit = state_kit("thief")
    state.pending_claim = state.my_pos
    record, message = thief_act(state, kit, step=5, sub_game=1, move_token="N")
    assert message.claim_response == {"claim": [3, 3], "caught": True}
    assert state.over and state.ending.result == "capture"
    assert state.my_pos == (3, 3)
    assert record["payload"]["move"] == "MOVE:STAY"
    assert record["payload"]["verdict"] == "settled"


def test_false_claim_stays_false_even_when_the_move_lands_on_the_claimed_cell():
    state, kit = state_kit("thief")
    state.pending_claim = (2, 3)
    _record, message = thief_act(state, kit, step=5, sub_game=1, move_token="N")
    assert message.claim_response == {"claim": [2, 3], "caught": False}
    assert not state.over
    assert state.my_pos == (2, 3)


# --- A6: equivocation and flood evidence surfaces and has consequences ---


def sealed(payload):
    return {"payload": payload, "nonce": "ab" * 16, "commit": commit(payload, "ab" * 16)}


def gateway_with(cfg=CFG):
    return Gateway(
        game_cfg=cfg, peer_cfg=PeerConfig(), role="police", group_id="cosmos77",
        group_name="cosmos77", client=object(), inbox=PeerInbox(),
    )


def survived_state():
    state, _kit = state_kit("police")
    state.their_turns = CFG.survival_threshold
    state.finish("survival", "thief", "thief claimed the survival threshold")
    return state


def full_trail():
    return [sealed({"step": s}) for s in range(1, CFG.survival_threshold + 1)]


def report_for(state):
    return SubGameReport(
        sub_game_number=1, my_role=state.role, result=state.ending.result,
        reason=state.ending.reason, steps=1, started_at="t0", ended_at="t1", records=[],
    )


def test_equivocation_refuses_log_verified_and_surfaces_in_the_report():
    gateway = gateway_with()
    state = survived_state()
    gateway.receiver.ingest({"step": 1, "commit": "aaa"})
    gateway.receiver.ingest({"step": 1, "commit": "bbb"})
    report = report_for(state)
    with patch(
        "cosmos77_cop.orchestrator.runtime.exchange_audits",
        return_value={"records": full_trail()},
    ):
        audit_phase(gateway, state, object(), report)
    assert report.equivocations == [[1, "aaa", "bbb"]]
    assert report.settlement.settled and report.settlement.result == "tamper_forfeit"
    assert not report.settlement.log_verified and report.settlement.tampered
    assert any("equivocation" in n for n in report.my_audit.notes)


def test_flood_violation_surfaces_without_failing_a_clean_audit():
    gateway = gateway_with()
    state = survived_state()
    gateway.receiver.ingest({"step": 99, "commit": "zzz"})
    report = report_for(state)
    with patch(
        "cosmos77_cop.orchestrator.runtime.exchange_audits",
        return_value={"records": full_trail()},
    ):
        audit_phase(gateway, state, object(), report)
    assert any("past-window flood at step 99" in v for v in report.violations)
    assert report.settlement.settled and report.settlement.log_verified


def test_survival_ending_requires_the_revealed_trail_to_reach_the_threshold():
    gateway = gateway_with()
    state = survived_state()
    report = report_for(state)
    short = [sealed({"step": s}) for s in (1, 2, 3)]
    with patch(
        "cosmos77_cop.orchestrator.runtime.exchange_audits", return_value={"records": short}
    ):
        audit_phase(gateway, state, object(), report)
    assert report.settlement.result == "tamper_forfeit"
    assert any("survival corroboration failed" in n for n in report.my_audit.notes)
