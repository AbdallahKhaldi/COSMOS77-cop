"""The report-compare ritual: must-match vs may-differ (kit digest §9; run after every series)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MUST_MATCH_TOP = ("game_uid", "game_id", "groups", "num_sub_games")
MUST_MATCH_ROW = (
    "sub_game_number",
    "roles",
    "result",
    "winner_group",
    "tie",
    "score",
    "log_files",
    "github_commit",
    "audit",
)
MUST_MATCH_FINAL = ("total_score", "sub_games_won", "ties", "winner_group", "series_tie")
MUST_MATCH_LEAGUE = ("first_meeting_between_groups", "diversity_reward_applied")


def compare_results(ours: dict[str, Any], theirs: dict[str, Any]) -> list[str]:
    """Every must-match divergence, as human-readable diffs (empty = ritual passes)."""
    diffs: list[str] = []
    for key in MUST_MATCH_TOP:
        if ours.get(key) != theirs.get(key):
            diffs.append(f"{key}: ours={ours.get(key)!r} theirs={theirs.get(key)!r}")
    my_rows = {r["sub_game_number"]: r for r in ours.get("sub_games", [])}
    their_rows = {r["sub_game_number"]: r for r in theirs.get("sub_games", [])}
    for n in sorted(set(my_rows) | set(their_rows)):
        mine, other = my_rows.get(n), their_rows.get(n)
        if mine is None or other is None:
            diffs.append(f"sub_game {n}: present on only one side")
            continue
        for key in MUST_MATCH_ROW:
            if mine.get(key) != other.get(key):
                diffs.append(
                    f"sub_game {n}.{key}: ours={mine.get(key)!r} theirs={other.get(key)!r}"
                )
    my_final, their_final = ours.get("final_result", {}), theirs.get("final_result", {})
    for key in MUST_MATCH_FINAL + MUST_MATCH_LEAGUE:
        if my_final.get(key) != their_final.get(key):
            diffs.append(f"final.{key}: ours={my_final.get(key)!r} theirs={their_final.get(key)!r}")
    mine_sha = (ours.get("mutual_agreement") or {}).get("sha256")
    theirs_sha = (theirs.get("mutual_agreement") or {}).get("sha256")
    if mine_sha != theirs_sha:
        diffs.append(f"mutual_agreement.sha256: ours={mine_sha} theirs={theirs_sha}")
    return diffs


def compare_files(our_path: str | Path, their_path: str | Path) -> list[str]:
    """Load two result artifacts and run the ritual."""
    ours = json.loads(Path(our_path).read_text(encoding="utf-8"))
    theirs = json.loads(Path(their_path).read_text(encoding="utf-8"))
    return compare_results(ours, theirs)
