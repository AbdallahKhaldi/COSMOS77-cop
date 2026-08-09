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
    equivocations: list[list[Any]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


def observe_batch(state: TurnState, kit: SideKit, bridge: object, batch: list[dict]) -> None:
    """Fold applied opponent turns into local knowledge, with bridge hooks.

    Honors ``play_sub_game``'s never-raises contract: a wire message that cannot be folded
    is recorded as a violation and skipped — hostile input never kills a series.
    """
    for wire in batch:
        try:
            observe_turn(state, kit, wire)
            note = getattr(bridge, "note_opponent_turn", None)
            if note is not None:
                note(state, kit, wire)
            view = getattr(bridge, "view_attachment", None)
            if view is not None:
                view.note_hint(str(wire.get("hint", "")))
            answer = wire.get("claim_response")
            if answer is not None and not answer.get("caught"):
                on_false = getattr(bridge, "note_claim_answered_false", None)
                claimed = answer.get("claim")
                if on_false is not None and isinstance(claimed, list):
                    on_false((int(claimed[0]), int(claimed[1])))
        except Exception as exc:  # hostile wire input must never escape the turn loop
            state.wire_violations.append(f"unfoldable turn at step {wire.get('step')}: {exc}")


def surface_wire_evidence(gateway: Gateway, state: TurnState, report: SubGameReport) -> None:
    """Copy receiver + turn-level violation evidence into the report — it must stay LOUD.

    Equivocations are (step, first_commit, second_commit) triples; violations carry the
    barrier/claim refusals and past-window floods. The log artifact's summary embeds both.
    """
    report.equivocations = [list(t) for t in gateway.receiver.equivocations]
    floods = [f"past-window flood at step {s}" for s in gateway.receiver.violations]
    report.violations = [*state.wire_violations, *floods]


def audit_phase(gateway: Gateway, state: TurnState, bridge: object, report: SubGameReport) -> None:
    """Both reveal, then both verify; corroborate the ending; settle the row (§2.8-2.9).

    Beyond the spec'd four layers: a survival ending demands the revealed thief trail
    actually reach the threshold, and equivocation evidence refuses ``log_verified``
    (kit delivery contract — "tampering evidence and must stay loud").
    """
    theirs = runtime.exchange_audits(
        gateway, gateway.records, state.ending.result, gateway.peer_cfg.watchdog_s
    )
    report.their_audit_arrived = theirs is not None
    if theirs is None:
        report.settlement = settled_outcome(state.ending.result, None, their_audit_arrived=False)
        surface_wire_evidence(gateway, state, report)
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
    if state.ending.result == "survival" and state.role == "police" and verdict.clean:
        top = max(
            (int(r["payload"].get("step", 0)) for r in report.opp_records
             if isinstance(r.get("payload"), dict)),
            default=0,
        )
        if top < state.cfg.survival_threshold:
            verdict = AuditReport("tampered", [], [
                f"survival corroboration failed: revealed trail reaches step {top} "
                f"of {state.cfg.survival_threshold}"
            ])
    if gateway.receiver.equivocations:
        verdict = AuditReport("tampered", [], [
            "equivocation evidence (step, first_commit, second_commit): "
            f"{[list(t) for t in gateway.receiver.equivocations]}"
        ])
    report.my_audit = verdict
    report.settlement = settled_outcome(state.ending.result, verdict, their_audit_arrived=True)
    surface_wire_evidence(gateway, state, report)
