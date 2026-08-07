"""Sub-game reporting: observation folding and the audit/settlement phase (layers 1-4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..crypto.audit import AuditReport, audit_records
from ..crypto.corroborate import corroborate_capture
from ..crypto.settle import Settlement, settled_outcome
from . import runtime
from .gateway import Gateway
from .turnactions import observe_turn
from .turnstate import SideKit, TurnState


@dataclass
class SubGameReport:
    """Everything one side knows about a finished sub-game (feeds the artifacts)."""

    sub_game_number: int
    my_role: str
    result: str
    reason: str
    steps: int
    started_at: str
    ended_at: str
    records: list[dict[str, Any]]
    opp_records: list[dict[str, Any]] = field(default_factory=list)
    my_audit: AuditReport | None = None
    their_audit_arrived: bool = False
    settlement: Settlement | None = None
    tokens: int = 0
    tracker_trace: list[list[int] | None] = field(default_factory=list)


def observe_batch(state: TurnState, kit: SideKit, bridge: object, batch: list[dict]) -> None:
    """Fold applied opponent turns into local knowledge, with bridge hooks."""
    for wire in batch:
        observe_turn(state, kit, wire)
        note = getattr(bridge, "note_opponent_turn", None)
        if note is not None:
            note(state, kit, wire)
        answer = wire.get("claim_response")
        if answer is not None and not answer.get("caught"):
            on_false = getattr(bridge, "note_claim_answered_false", None)
            claimed = answer.get("claim")
            if on_false is not None and isinstance(claimed, list):
                on_false((int(claimed[0]), int(claimed[1])))


def audit_phase(gateway: Gateway, state: TurnState, bridge: object, report: SubGameReport) -> None:
    """Both reveal, then both verify; corroborate the ending; settle the row (§2.8-2.9)."""
    theirs = runtime.exchange_audits(
        gateway, gateway.records, state.ending.result, gateway.peer_cfg.watchdog_s
    )
    report.their_audit_arrived = theirs is not None
    if theirs is None:
        report.settlement = settled_outcome(state.ending.result, None, their_audit_arrived=False)
        return
    report.opp_records = list(theirs.get("records") or [])
    verdict = audit_records(
        report.opp_records,
        gateway.received_commits,
        grid_size=state.cfg.grid_size,
        barriers_max=state.cfg.max_barriers,
        max_steps=state.cfg.max_moves,
    )
    if state.ending.result == "capture" and state.role == "police" and verdict.clean:
        trail = [
            r["payload"]["position"]
            for r in report.opp_records
            if "position" in r.get("payload", {})
        ]
        ok, reason = corroborate_capture(
            state.final_response or {},
            trail_end=(int(trail[-1][0]), int(trail[-1][1])) if trail else None,
            cop_claimed_cell=getattr(bridge, "my_last_claim", None),
            barrier_cells=set(state.board.barriers),
            grid_size=state.cfg.grid_size,
        )
        if not ok:
            verdict = AuditReport("tampered", [], [f"ending corroboration failed: {reason}"])
    report.my_audit = verdict
    report.settlement = settled_outcome(state.ending.result, verdict, their_audit_arrived=True)
