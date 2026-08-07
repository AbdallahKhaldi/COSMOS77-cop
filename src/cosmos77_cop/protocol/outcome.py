"""Result-row semantics shared by reports and settlement (rule 48; kit SPEC §6/§9).

Zeroed rows (timeout / technical_loss / tamper_forfeit) are SANCTIONS, not ties:
``tie: false, winner_group: null``. ``ties`` counts tie-SCORED rows only; totals are always
derived from the fixed table, never declared.
"""

from __future__ import annotations

from typing import Any

RESULT_CAPTURE = "capture"
RESULT_SURVIVAL = "survival"
ZEROED = ("timeout", "technical_loss", "tamper_forfeit")


def row_score(
    result: str, cop_group: str, thief_group: str, scoring: dict[str, int]
) -> dict[str, int]:
    """Per-group points for one sub-game row from the fixed table."""
    if result == RESULT_CAPTURE:
        return {cop_group: scoring["capture_cop"], thief_group: scoring["capture_thief"]}
    if result == RESULT_SURVIVAL:
        return {cop_group: scoring["survival_cop"], thief_group: scoring["survival_thief"]}
    zero = scoring["technical_loss"]
    return {cop_group: zero, thief_group: zero}


def row_winner(result: str, cop_group: str, thief_group: str) -> str | None:
    """The winning group for one row; zeroed rows carry ``None``."""
    if result == RESULT_CAPTURE:
        return cop_group
    if result == RESULT_SURVIVAL:
        return thief_group
    return None


def row_is_tie(result: str) -> bool:
    """Sub-game rows never tie under the fixed table; zeroed rows are sanctions, not ties."""
    return False


def aggregate(rows: list[dict[str, Any]], groups: list[str]) -> dict[str, Any]:
    """Derive the series aggregate (totals, wins, ties, winner, series_tie) from scored rows."""
    totals = {g: 0 for g in groups}
    wins = {g: 0 for g in groups}
    ties = 0
    for row in rows:
        for group, pts in row["score"].items():
            totals[group] += int(pts)
        if row.get("tie"):
            ties += 1
        elif row.get("winner_group") in wins:
            wins[row["winner_group"]] += 1
    a, b = sorted(groups)
    series_tie = totals[a] == totals[b]
    winner = None if series_tie else max(groups, key=lambda g: totals[g])
    return {
        "total_score": totals,
        "sub_games_won": wins,
        "ties": ties,
        "winner_group": winner,
        "series_tie": series_tie,
    }


def apply_series_tie_rule(agg: dict[str, Any], tie_bonus: int) -> dict[str, Any]:
    """Our declared ``series_add`` rule: on a tied series, +*tie_bonus* each ADDED to totals."""
    if not agg["series_tie"]:
        return agg
    updated = dict(agg)
    updated["total_score"] = {g: v + tie_bonus for g, v in agg["total_score"].items()}
    return updated
