"""Role-split closing: the closer assembles rows it did not play from the shared logs."""

import json
from pathlib import Path

from cosmos77_cop.crypto.settle import Settlement
from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.orchestrator.peerconf import PeerConfig
from cosmos77_cop.orchestrator.series import SeriesDriver
from cosmos77_cop.orchestrator.subreport import SubGameReport
from cosmos77_cop.report.artifacts import ArtifactWriter
from cosmos77_cop.report.finish import finish_series

REPO = Path(__file__).resolve().parents[2]


def make_driver(tmp_path):
    raw = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    driver = SeriesDriver(
        game_cfg=from_dict(raw),
        peer_cfg=PeerConfig(),
        gid_a="cosmos77",
        gid_b="rival",
        out_dir=tmp_path,
        code_version="a" * 40,
        alternate_labels=False,
    )
    return driver, raw


def own_report(window, result="survival"):
    return SubGameReport(
        sub_game_number=window,
        my_role="police",
        result=result,
        reason="test",
        steps=35,
        started_at="t0",
        ended_at="t1",
        records=[],
        settlement=Settlement(True, result, log_verified=True, tampered=False),
    )


def sibling_row(window):
    return {
        "sub_game_number": window,
        "roles": {"cosmos77": "thief", "rival": "police"},
        "started_at": "t0",
        "ended_at": "t1",
        "result": "survival",
        "winner_group": "cosmos77",
        "tie": False,
        "steps": 35,
        "github_commit": {"cosmos77": "a" * 40},
        "tokens": {"cosmos77": 0, "rival": 0},
        "score": {"cosmos77": 10, "rival": 5},
        "log_files": {"cosmos77": "x", "rival": "x"},
        "audit": {"log_verified": True, "tampered": False},
    }


def write_sibling_log(tmp_path, driver, window):
    log = {"summary": {"settled": True, "row": sibling_row(window)}}
    name = f"log_{driver.gid}_g{window:02d}.json"
    (tmp_path / name).write_text(json.dumps(log), encoding="utf-8")


def test_closer_assembles_sibling_rows_and_requires_all_windows(tmp_path):
    driver, raw = make_driver(tmp_path)
    driver.reports = [own_report(1), own_report(3)]
    writer = ArtifactWriter(
        tmp_path, gid=driver.gid, uid="u", github={}, counted=False, reason="friendly"
    )
    identity = {"group_name": "cosmos77", "members": [], "repos": {}, "mcp_servers": {}}
    partial = finish_series(
        driver, writer, raw_cfg=raw, my_gid="cosmos77", my_identity=identity,
        peer_identity=None, expected_windows=3,
    )
    assert not partial["settled"]
    write_sibling_log(tmp_path, driver, 2)
    complete = finish_series(
        driver, writer, raw_cfg=raw, my_gid="cosmos77", my_identity=identity,
        peer_identity=None, expected_windows=3,
    )
    assert complete["settled"]
    assert [r["sub_game_number"] for r in complete["rows"]] == [1, 2, 3]
    result = json.loads((tmp_path / f"result_{driver.gid}.json").read_text(encoding="utf-8"))
    assert result["final_result"]["total_score"]["cosmos77"] >= 10


def test_fixed_labels_keep_our_group_police_every_window(tmp_path):
    driver, _ = make_driver(tmp_path)
    assert driver.window_roles(1) == ("cosmos77", "rival")
    assert driver.window_roles(2) == ("cosmos77", "rival")
    alternating = SeriesDriver(
        game_cfg=driver.cfg,
        peer_cfg=PeerConfig(),
        gid_a="cosmos77",
        gid_b="rival",
        out_dir=tmp_path,
        code_version="a" * 40,
        alternate_labels=True,
    )
    assert alternating.window_roles(1) == ("cosmos77", "rival")
    assert alternating.window_roles(2) == ("rival", "cosmos77")
