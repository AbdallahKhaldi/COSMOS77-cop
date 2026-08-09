"""Thief-side turn primitives: honest claim answers, survival claims, rule-46/47 concessions."""

from __future__ import annotations

from typing import Any

from ..engine import capture
from ..engine.rules import apply_move
from ..net.messages import TurnMessage
from ..protocol.sealing import INTENT_TRUTH, VERDICT_MOVED, VERDICT_SETTLED
from .turnactions import seal_and_wire
from .turnstate import SideKit, TurnState


def thief_act(
    state: TurnState,
    kit: SideKit,
    *,
    step: int,
    sub_game: int,
    move_token: str,
) -> tuple[dict, TurnMessage]:
    """Answer any pending claim against our position AT CLAIM RECEIPT, then act (rules 21-22).

    The claim was made about where we stood when it arrived — never about where our next
    move lands. A true co-location claim settles NOW: the answer rides a terminal STAY (kit
    terminal-message semantics) and the thief takes no further move. Only a false answer
    lets this turn proceed as a normal move.
    """
    claim_answer: dict[str, Any] | None = None
    if state.pending_claim is not None:
        claim_answer = {
            "claim": [state.pending_claim[0], state.pending_claim[1]],
            "caught": state.pending_claim == state.my_pos,
        }
    win: dict[str, Any] | None = None
    verdict = VERDICT_MOVED
    if claim_answer is not None and claim_answer["caught"]:
        state.finish("capture", "police", "answered a true co-location claim")
        verdict = VERDICT_SETTLED
        move_token = "STAY"
    else:
        state.my_pos = apply_move(state.board, state.my_pos, move_token)
        state.my_moves += 1
        if state.my_moves >= state.cfg.survival_threshold:
            win = {"type": "survival"}
            state.finish("survival", "thief", "reached the survival threshold")
            verdict = VERDICT_SETTLED
    hint = kit.hints.hint_for_step(step, sub_game)
    record, message = seal_and_wire(
        state, kit, step=step, sub_game=sub_game, move_token=move_token,
        verdict=verdict, intent=hint.intent, hint=hint.text,
        claim_response=claim_answer, win_claim=win,
    )
    state.pending_claim = None
    return record, message


def thief_concede(
    state: TurnState, kit: SideKit, *, step: int, sub_game: int
) -> tuple[dict, TurnMessage]:
    """The obligatory rule-46/47 concession final (playbook §0.5): name our own cell, settle."""
    state.finish("capture", "police", state.ending.reason if state.ending else "boxed in (rule 47)")
    response = capture.concession_payload(state.my_pos)
    hint = kit.hints.hint_for_step(step, sub_game)
    return seal_and_wire(
        state, kit, step=step, sub_game=sub_game, move_token="STAY",
        verdict=VERDICT_SETTLED, intent=INTENT_TRUTH, hint=hint.text,
        claim_response=response,
    )
