"""Result rows + final aggregate from played sub-game reports (§2.10; totals always derived)."""

from __future__ import annotations

from typing import Any

from ..engine.config import GameConfig
from ..orchestrator.subreport import SubGameReport
from ..protocol.consensus import consensus_scope, report_consensus_signature
from ..protocol.ids import artifact_filenames
from ..protocol.outcome import aggregate, apply_series_tie_rule, row_score, row_winner


def _their_commit(report: SubGameReport) -> str | None:
    for record in report.opp_records:
        payload = record.get("payload", {})
        if payload.get("step") == 0:
            return payload.get("github_commit") or payload.get("code_version")
    return None


def row_from_report(
    report: SubGameReport,
    *,
    cfg: GameConfig,
    police_gid: str,
    thief_gid: str,
    gid: str,
    my_gid: str,
    opp_gid: str,
    my_commit: str,
) -> dict[str, Any]:
    """One result row in the kit example shape."""
    settlement = report.settlement
    result = settlement.result if settlement and settlement.settled else report.result
    commits = {my_gid: my_commit}
    theirs = _their_commit(report)
    if theirs:
        commits[opp_gid] = theirs
    log_name = artifact_filenames(gid, report.sub_game_number)["log"]
    return {
        "sub_game_number": report.sub_game_number,
        "roles": {police_gid: "police", thief_gid: "thief"},
        "started_at": report.started_at,
        "ended_at": report.ended_at,
        "result": result,
        "winner_group": row_winner(result, police_gid, thief_gid),
        "tie": False,
        "steps": report.steps,
        "github_commit": commits,
        "tokens": {my_gid: report.tokens, opp_gid: 0},
        "score": row_score(result, police_gid, thief_gid, cfg.scoring),
        "log_files": {my_gid: log_name, opp_gid: log_name},
        "audit": {
            "log_verified": bool(settlement and settlement.log_verified),
            "tampered": bool(settlement and settlement.tampered),
        },
    }


def final_result_block(
    rows: list[dict[str, Any]],
    *,
    cfg: GameConfig,
    gid_a: str,
    gid_b: str,
    counted: bool,
    my_gid: str | None = None,
    num_games_declared: int | None = None,
    first_meeting: bool = True,
) -> dict[str, Any]:
    """The derived aggregate + league fields (disarmed on friendlies, rules 37-38).

    ``games_played_including_this``: OUR count is the declaration's exclusive ledger count
    + 1 (the §2.10 identity); the OPPONENT'S is null — never fabricated (kit SPEC §6.2,
    "null is not 0/1"). ``first_meeting_between_groups`` is the rule-52 ledger's answer.
    """
    groups = sorted([gid_a, gid_b])
    agg = apply_series_tie_rule(aggregate(rows, groups), cfg.scoring["tie_score"])
    tokens = {g: sum(int(r["tokens"].get(g, 0)) for r in rows) for g in groups}
    winner = agg["winner_group"]
    counts: dict[str, int | None] = dict.fromkeys(groups)
    if counted and my_gid in counts:
        counts[my_gid] = int(num_games_declared or 0) + 1
    return {
        **agg,
        "tokens_total_series": tokens,
        "games_played_including_this": counts,
        "first_meeting_between_groups": bool(first_meeting),
        "diversity_reward_applied": {g: bool(counted and g == winner) for g in groups},
    }


def mutual_agreement_block(
    gid: str, agg: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """The consensus hash over exactly what both teams must agree on (§2.5 scope)."""
    scope_agg = {
        k: agg[k] for k in ("total_score", "sub_games_won", "ties", "winner_group", "series_tie")
    }
    scope = consensus_scope(gid, scope_agg, rows)
    return {"sha256": report_consensus_signature(scope), "confirmed": True}


def all_settled(reports: list[SubGameReport]) -> bool:
    """Rule-35 guard: a series with any unsettled PLAYED window emits nothing."""
    return all(r.settlement is not None and r.settlement.settled for r in reports)
