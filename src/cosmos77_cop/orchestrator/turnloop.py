"""One live sub-game from one side: thief-first turns, message-driven endings, mutual audit."""

from __future__ import annotations

from ..crypto.settle import settled_outcome
from ..engine.capture import is_rule47_boxed
from ..net.messages import TurnMessage, now_iso
from . import runtime
from .gateway import Gateway
from .subreport import SubGameReport, audit_phase, observe_batch
from .turnactions import police_act, thief_act, thief_concede
from .turnstate import SideKit, TurnState


def _send(gateway: Gateway, state: TurnState, record: dict, message: TurnMessage) -> bool:
    gateway.records.append(record)
    if not runtime.send_turn(gateway, message.to_wire()):
        state.finish("timeout", None, "our turn could not be delivered")
        return False
    return True


def _police_loop(gateway: Gateway, state: TurnState, kit: SideKit, bridge: object) -> None:
    step = 0
    guard = 2 * state.cfg.survival_threshold + 6
    while not state.over and step < guard:
        batch = runtime.await_applied(gateway, gateway.peer_cfg.turn_timeout_s)
        if not batch:
            state.finish("timeout", None, "opponent turn deadline expired")
            return
        observe_batch(state, kit, bridge, batch)
        if state.over:
            return
        step += 1
        action = bridge.decide(state, kit)
        record, message = police_act(
            state, kit, step=step, sub_game=gateway.sub_game_number, brain_action=action
        )
        if not _send(gateway, state, record, message):
            return
    if not state.over:
        state.finish("timeout", None, "step guard exhausted")


def _thief_loop(gateway: Gateway, state: TurnState, kit: SideKit, bridge: object) -> None:
    step = 0
    guard = state.cfg.survival_threshold + 3
    while not state.over and step < guard:
        step += 1
        concede_now = is_rule47_boxed(state.board, state.my_pos)
        action = None if concede_now else bridge.decide(state, kit)
        if concede_now or action.kind == "concede":
            record, message = thief_concede(
                state, kit, step=step, sub_game=gateway.sub_game_number
            )
            _send(gateway, state, record, message)
            return
        record, message = thief_act(
            state,
            kit,
            step=step,
            sub_game=gateway.sub_game_number,
            move_token=action.move_token or "STAY",
        )
        if not _send(gateway, state, record, message) or state.over:
            return
        batch = runtime.await_applied(gateway, gateway.peer_cfg.turn_timeout_s)
        if not batch:
            state.finish("timeout", None, "opponent turn deadline expired")
            return
        observe_batch(state, kit, bridge, batch)
        if state.over and state.ending and state.ending.reason.startswith("rule_46"):
            step += 1
            record, message = thief_concede(
                state, kit, step=step, sub_game=gateway.sub_game_number
            )
            _send(gateway, state, record, message)
            return
    if not state.over:
        state.finish("timeout", None, "step guard exhausted")


def play_sub_game(
    gateway: Gateway, state: TurnState, kit: SideKit, bridge: object, step0_record: dict
) -> SubGameReport:
    """Handshake, play to an ending, exchange audits, settle. Never raises mid-series."""
    started = now_iso()
    gateway.records.append(step0_record)
    if not runtime.handshake(gateway):
        state.finish("technical_loss", None, "handshake failed")
    elif state.role == "police":
        _police_loop(gateway, state, kit, bridge)
    else:
        _thief_loop(gateway, state, kit, bridge)
    report = SubGameReport(
        sub_game_number=gateway.sub_game_number,
        my_role=state.role,
        result=state.ending.result,
        reason=state.ending.reason,
        steps=state.my_moves if state.role == "thief" else state.their_turns,
        started_at=started,
        ended_at=now_iso(),
        records=list(gateway.records),
        tokens=kit.meter.total_series,
        tracker_trace=list(state.tracker_trace),
    )
    if state.ending.result in ("capture", "survival"):
        audit_phase(gateway, state, bridge, report)
    else:
        report.settlement = settled_outcome(state.ending.result, None, their_audit_arrived=False)
    return report
