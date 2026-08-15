"""Series completion: configs, declaration, result — or NOTHING when unsettled (rule 35)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..net.messages import now_iso
from ..orchestrator.series import SeriesDriver
from ..protocol.ids import artifact_filenames
from .artifacts import ArtifactWriter
from .declaration import _group_block, _peer_commit, _peer_hardware
from .rows import all_settled, final_result_block, mutual_agreement_block, row_from_report


def finish_series(
    driver: SeriesDriver,
    writer: ArtifactWriter,
    *,
    raw_cfg: dict[str, Any],
    my_gid: str,
    my_identity: dict[str, Any],
    peer_identity: dict[str, Any] | None,
    expected_windows: int | None = None,
) -> dict[str, Any]:
    """Write configs + declaration always; the result ONLY when every window settled."""
    pair = sorted([driver.gid_a, driver.gid_b])
    locked = dict(raw_cfg)
    locked["agreed_between"] = pair
    # The ACTUAL windows this side played (split topology: e.g. 2,4,6), never a
    # dense 1..N — misnumbered config artifacts break the opponent's bundle audit.
    for window in sorted({int(r.sub_game_number) for r in driver.reports}):
        writer.write_config(
            window,
            {**locked, "game_id": driver.gid, "game_uid": writer.uid, "sub_game_number": window},
        )

    theirs = peer_identity or {}
    opp_gid = pair[1] if my_gid == pair[0] else pair[0]
    their_hw = _peer_hardware(driver)
    declaration = writer.base_envelope(
        "Pre-game declaration: identity, members, repos, endpoints, hardware, truthful counts."
    )
    declaration.update(
        {
            "declaration_type": "pre_game_declaration",
            "report_type": "declaration",
            "timezone": "Asia/Jerusalem",
            "game_started_at": driver.reports[0].started_at if driver.reports else now_iso(),
            "num_sub_games": driver.cfg.num_games,
            "max_tokens_per_series": driver.cfg.token_budget_per_series,
            "groups": {
                "group_1": _group_block(
                    my_gid,
                    my_identity,
                    driver.hardware,
                    driver.code_version,
                    driver.num_games_declared,
                ),
                "group_2": _group_block(
                    opp_gid,
                    theirs.get("identity", {}) if isinstance(theirs, dict) else {},
                    their_hw,
                    _peer_commit(driver) or "unknown",
                    None,
                ),
            },
        }
    )
    writer.write_declaration(declaration)

    own_rows: dict[int, dict[str, Any]] = {}
    for r in driver.reports:
        police_gid, thief_gid = driver.window_roles(r.sub_game_number)
        own_rows[r.sub_game_number] = row_from_report(
            r,
            cfg=driver.cfg,
            police_gid=police_gid,
            thief_gid=thief_gid,
            gid=driver.gid,
            my_gid=my_gid,
            opp_gid=opp_gid,
            my_commit=driver.code_version,
        )
    expected = expected_windows or driver.cfg.num_games
    rows = []
    settled = all_settled(driver.reports)
    for window in range(1, expected + 1):
        if window in own_rows:
            rows.append(own_rows[window])
            continue
        log_path = Path(writer.out_dir) / artifact_filenames(driver.gid, window)["log"]
        if not log_path.exists():
            settled = False
            continue
        log = json.loads(log_path.read_text(encoding="utf-8"))
        row = (log.get("summary") or {}).get("row")
        if row is None or not (log.get("summary") or {}).get("settled"):
            settled = False
            continue
        rows.append(row)
    rows.sort(key=lambda r: r["sub_game_number"])
    complete = settled and len(rows) == expected
    summary: dict[str, Any] = {"rows": rows, "settled": complete}
    if summary["settled"] and rows:
        final = final_result_block(
            rows,
            cfg=driver.cfg,
            gid_a=driver.gid_a,
            gid_b=driver.gid_b,
            counted=writer.league["counted"],
            my_gid=my_gid,
            num_games_declared=driver.num_games_declared,
            first_meeting=getattr(driver, "first_meeting", True),
        )
        result = writer.base_envelope("Final series result - email the compact canonical bytes.")
        result.update(
            {
                "report_type": "final_game_result",
                "timezone": "Asia/Jerusalem",
                "groups": pair,
                "num_sub_games": driver.cfg.num_games,
                "sub_games": rows,
                "final_result": final,
                "mutual_agreement": mutual_agreement_block(driver.gid, final, rows),
            }
        )
        writer.write_result(result)
        summary["final_result"] = final
        summary["result_file"] = artifact_filenames(driver.gid)["result"]
    return summary


