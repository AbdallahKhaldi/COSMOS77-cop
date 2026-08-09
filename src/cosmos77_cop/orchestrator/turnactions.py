"""One side's act/observe primitives for the live turn loop (message-driven, local truth only)."""

from __future__ import annotations

from typing import Any, Protocol

from ..crypto.nonce import new_nonce
from ..engine import capture
from ..engine.board import Coord
from ..engine.rules import apply_move
from ..net.messages import TurnMessage, now_iso
from ..protocol.sealing import (
    VERDICT_BARRIER,
    VERDICT_MOVED,
    build_turn_payload,
    commit,
)
from .turnstate import SideKit, TurnState


def seal_and_wire(
    state: TurnState,
    kit: SideKit,
    *,
    step: int,
    sub_game: int,
    move_token: str,
    verdict: str,
    intent: str,
    hint: str,
    barrier_placed: Coord | None = None,
    capture_claim: Coord | None = None,
    claim_response: dict[str, Any] | None = None,
    win_claim: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], TurnMessage]:
    """Seal our record and build the matching wire message (grid from the scent flow)."""
    payload = build_turn_payload(
        step=step,
        role=state.role,
        sub_game=sub_game,
        grid_size=state.cfg.grid_size,
        self_pos=state.my_pos,
        barriers=sorted(state.board.barriers),
        move=f"MOVE:{move_token}" if verdict != VERDICT_BARRIER else f"BARRIER:{barrier_placed}",
        intent=intent,
        hint=hint,
        verdict=verdict,
    )
    nonce = new_nonce()
    record = {"payload": payload, "nonce": nonce, "commit": commit(payload, nonce)}
    message = TurnMessage(
        step=step,
        sender=state.role,
        commit=record["commit"],
        hint=hint,
        smell_grid=kit.flow.step_emit(state.my_pos),
        timestamp=now_iso(),
        barrier_placed=list(barrier_placed) if barrier_placed else None,
        capture_claim=list(capture_claim) if capture_claim else None,
        claim_response=claim_response,
        win_claim=win_claim,
    )
    return record, message


def _fold_barrier(state: TurnState, sender: str, cell: list[Any]) -> None:
    """Validate and absorb one declared barrier, or record why it is refused (rule 15).

    Refused declarations become violation evidence, never board state: boxed/rule-46
    checks see only VALIDATED barriers, so a forged capture is structurally impossible.
    """
    if state.role != "thief" or sender != "police":
        state.wire_violations.append(f"barrier declared by non-police sender {sender!r}")
        return
    placed = (int(cell[0]), int(cell[1]))
    if not state.board.in_bounds(placed):
        state.wire_violations.append(f"declared barrier {placed} is off-board")
    elif placed in state.board.barriers:
        state.wire_violations.append(f"declared barrier {placed} duplicates an existing barrier")
    elif state.their_barriers >= state.cfg.max_barriers:
        quota = state.cfg.max_barriers
        state.wire_violations.append(f"declared barrier {placed} exceeds the quota of {quota}")
    else:
        state.their_barriers += 1
        state.board.add_barrier(placed)
        if capture.is_rule46(placed, state.my_pos):
            state.finish("capture", "police", "rule_46 barrier on our cell")


def observe_turn(state: TurnState, kit: SideKit, wire: dict[str, Any]) -> None:
    """Fold one applied opponent turn into local knowledge and detect message-driven endings."""
    message = TurnMessage.from_wire(wire)
    state.their_turns += 1
    kit.flow.observe(message.smell_grid)
    kit.tracker.observe_grid(message.smell_grid)
    cell, confidence = kit.tracker.estimate()
    state.tracker_trace.append([cell[0], cell[1]] if confidence == "exact" and cell else None)
    if message.hint and cell is not None and confidence == "exact":
        kit.liar.observe(message.hint, cell, state.cfg.grid_size)
    if message.barrier_placed is not None:
        _fold_barrier(state, message.sender, message.barrier_placed)
    if message.capture_claim is not None:
        state.pending_claim = (int(message.capture_claim[0]), int(message.capture_claim[1]))
    if message.claim_response is not None and message.claim_response.get("caught"):
        state.final_response = dict(message.claim_response)
        state.finish("capture", "police", "thief admitted capture")
    if message.win_claim is not None and message.win_claim.get("type") == "survival":
        if state.their_turns >= state.cfg.survival_threshold:
            state.finish("survival", "thief", "thief claimed the survival threshold")
        else:
            note = f"premature survival claim at opponent turn {state.their_turns}"
            state.wire_violations.append(f"{note} (threshold {state.cfg.survival_threshold})")


class CopActionLike(Protocol):
    """The shape of the cop brain's decision (kept structural so the file mirrors cleanly)."""

    kind: str
    move_token: str | None
    barrier_cell: Coord | None
    capture_claim: Coord | None


def police_act(
    state: TurnState,
    kit: SideKit,
    *,
    step: int,
    sub_game: int,
    brain_action: CopActionLike,
) -> tuple[dict, TurnMessage]:
    """Convert a CopAction into an engine change + sealed wire turn."""
    hint = kit.hints.hint_for_step(step, sub_game)
    if brain_action.kind == "barrier":
        cell = brain_action.barrier_cell
        state.board.add_barrier(cell)
        state.barriers_left -= 1
        state.my_moves += 1
        return seal_and_wire(
            state, kit, step=step, sub_game=sub_game, move_token="STAY",
            verdict=VERDICT_BARRIER, intent=hint.intent, hint=hint.text, barrier_placed=cell,
        )
    state.my_pos = apply_move(state.board, state.my_pos, brain_action.move_token)
    state.my_moves += 1
    return seal_and_wire(
        state, kit, step=step, sub_game=sub_game, move_token=brain_action.move_token,
        verdict=VERDICT_MOVED, intent=hint.intent, hint=hint.text,
        capture_claim=brain_action.capture_claim,
    )
