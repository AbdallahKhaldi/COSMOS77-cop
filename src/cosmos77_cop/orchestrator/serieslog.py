"""Writing one window's log artifact — kept out of the driver so both stay under the cap."""

from __future__ import annotations

from typing import Any

from ..crypto.nonce import new_nonce
from ..crypto.step0 import build_step0
from ..protocol.sealing import commit
from ..report.rows import row_from_report
from .brainbridge import ROLE
from .subreport import SubGameReport

NO_AUDIT = "the opponent's reveal never arrived; there was nothing to verify"


def audit_block(report: SubGameReport) -> dict[str, Any]:
    """The audit's VERDICT as evidence, not merely its boolean shadow (layers 1-4).

    ``log_verified: true`` alone tells a grader nothing about what the four layers examined or
    what they would have said had a step failed. The verdict, the failing steps and the notes
    are the audit's actual output; a window whose peer never revealed carries a null verdict
    rather than a silent ``false``, which would read as an accusation.
    """
    verdict = report.my_audit
    return {
        "verdict": verdict.verdict if verdict else None,
        "failed_steps": list(verdict.failed_steps) if verdict else [],
        "notes": list(verdict.notes) if verdict else [NO_AUDIT],
        "their_audit_arrived": bool(report.their_audit_arrived),
    }


def write_window_log(driver: object, window: int, report: SubGameReport) -> None:
    """Write the per-sub-game log, embedding the result row the closer may need."""
    if driver.writer is None:
        return
    settlement = report.settlement
    police_gid, thief_gid = driver.window_roles(window)
    my_gid = police_gid if ROLE == "police" else thief_gid
    opp_gid = thief_gid if ROLE == "police" else police_gid
    driver.writer.write_log(
        window,
        summary={
            "result": report.result,
            "my_role": report.my_role,
            "steps": report.steps,
            "reason": report.reason,
            "settled": bool(settlement and settlement.settled),
            "log_verified": bool(settlement and settlement.log_verified),
            "tampered": bool(settlement and settlement.tampered),
            "audit": audit_block(report),
            "equivocations": report.equivocations,
            "violations": report.violations,
            "tracker_trace": report.tracker_trace,
            "row": row_from_report(
                report,
                cfg=driver.cfg,
                police_gid=police_gid,
                thief_gid=thief_gid,
                gid=driver.gid,
                my_gid=my_gid,
                opp_gid=opp_gid,
                my_commit=driver.code_version,
            ),
        },
        records=report.records,
        opponent_records=report.opp_records,
    )


def note_peer_repos(driver: object, window: int) -> None:
    """Map the peer's declared repos to THEIR gid in ``links.github`` (rule 49) — never ours.

    An opponent that declared no repos gets no entry: their links are not invented for them.
    """
    police_gid, thief_gid = driver.window_roles(window)
    opp_gid = thief_gid if ROLE == "police" else police_gid
    repos = ((driver.peer_identity or {}).get("identity") or {}).get("repos")
    if driver.writer is not None and isinstance(repos, dict) and repos:
        driver.writer.links["github"][opp_gid] = dict(repos)


def sealed_step0(driver: object, group_id: str, window: int) -> dict[str, Any]:
    """The sealed step-0 declaration for one window (rules 24 + 53)."""
    payload = build_step0(
        sub_game_number=window,
        group_name=group_id,
        model=driver.hints.declared_model,
        code_version=driver.code_version,
        num_games_declared=driver.num_games_declared,
        spec=driver.hardware,
    )
    nonce = new_nonce()
    return {"payload": payload, "nonce": nonce, "commit": commit(payload, nonce)}
