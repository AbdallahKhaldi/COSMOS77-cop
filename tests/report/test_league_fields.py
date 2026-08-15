"""Rules 37-38/52 league fields: ledger-truthful counts, null for the opponent, ledger
advancement on the confirmed counted send, and repeat-opponent arming refusal."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cosmos77_cop.arming import ArmingError, first_meeting, serve_posture
from cosmos77_cop.commands import report_cmd
from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.protocol.canonical import canonical_bytes
from cosmos77_cop.report.ledger import Ledger
from cosmos77_cop.report.rows import final_result_block

REPO = Path(__file__).resolve().parents[2]
CFG = from_dict(json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8")))


def row(window):
    return {
        "sub_game_number": window,
        "roles": {"cosmos77": "police", "rival": "thief"},
        "started_at": "t0", "ended_at": "t1",
        "result": "survival", "winner_group": "rival", "tie": False, "steps": 35,
        "github_commit": {"cosmos77": "a" * 40},
        "tokens": {"cosmos77": 0, "rival": 0},
        "score": {"cosmos77": 5, "rival": 10},
        "log_files": {"cosmos77": "x", "rival": "x"},
        "audit": {"log_verified": True, "tampered": False},
    }


def test_counted_counts_are_ours_plus_one_and_null_for_the_opponent():
    final = final_result_block(
        [row(1)], cfg=CFG, gid_a="cosmos77", gid_b="rival", counted=True,
        my_gid="cosmos77", num_games_declared=1, first_meeting=True,
    )
    assert final["games_played_including_this"] == {"cosmos77": 2, "rival": None}
    assert final["first_meeting_between_groups"] is True


def test_friendly_counts_stay_all_null_and_first_meeting_stays_truthful():
    final = final_result_block(
        [row(1)], cfg=CFG, gid_a="cosmos77", gid_b="rival", counted=False,
        my_gid="cosmos77", num_games_declared=3, first_meeting=False,
    )
    assert final["games_played_including_this"] == {"cosmos77": None, "rival": None}
    assert final["first_meeting_between_groups"] is False


def test_the_opponents_token_count_is_null_not_zero():
    """Kit SPEC §6.2: null is UNCLAIMED, 0 is a claim. We meter our own consumption; the
    opponent's is unknowable from here, so a hardcoded 0 was a false measurement."""
    from cosmos77_cop.crypto.settle import Settlement
    from cosmos77_cop.orchestrator.subreport import SubGameReport
    from cosmos77_cop.report.rows import row_from_report

    report = SubGameReport(
        sub_game_number=1, my_role="police", result="capture", reason="caught", steps=3,
        started_at="t0", ended_at="t1", records=[], opp_records=[], tokens=1234,
        settlement=Settlement(True, "capture", True, False),
    )
    built = row_from_report(
        report, cfg=CFG, police_gid="cosmos77", thief_gid="rival", gid="a-vs-b",
        my_gid="cosmos77", opp_gid="rival", my_commit="a" * 40,
    )
    # numeric BOTH sides: the kit's check_artifacts.py (the mandatory bundle gate)
    # refuses non-numeric tokens maps; 0 = unmeasured, the filed-artifact convention
    assert built["tokens"] == {"cosmos77": 1234, "rival": 0}
    final = final_result_block(
        [built], cfg=CFG, gid_a="cosmos77", gid_b="rival", counted=False, my_gid="cosmos77",
    )
    assert final["tokens_total_series"] == {"cosmos77": 1234, "rival": 0}
    assert json.loads(canonical_bytes(final))["tokens_total_series"]["rival"] == 0


def test_first_meeting_reads_the_committed_ledger(tmp_path):
    assert first_meeting("rival", str(tmp_path)) is True
    ledger = Ledger.load(tmp_path / "artifacts" / "league_ledger.json")
    ledger.record(opponent="rival", game_id="g", game_uid="u", won=True, settled_at="t")
    assert first_meeting("rival", str(tmp_path)) is False


@patch("cosmos77_cop.arming.is_dirty", return_value=False)
@patch("cosmos77_cop.arming.has_credentials", return_value=True)
def test_counted_arming_refuses_a_repeat_opponent(_creds, _dirty, tmp_path, monkeypatch):
    monkeypatch.setattr("cosmos77_cop.arming.token_ready", lambda root=".": True)
    ledger = Ledger.load(tmp_path / "artifacts" / "league_ledger.json")
    ledger.record(opponent="rival", game_id="g", game_uid="u", won=True, settled_at="t")
    with pytest.raises(ArmingError, match="rule 52"):
        serve_posture(
            config_counted=True, cli_counted=True, opponent="rival", root=str(tmp_path)
        )
    fresh = serve_posture(
        config_counted=True, cli_counted=True, opponent="newteam", root=str(tmp_path)
    )
    assert fresh.counted


def counted_result_body():
    return {
        "game_id": "SMNGRP05-vs-cosmos77",
        "game_uid": "u" * 8,
        "league": {"counted": True},
        "mutual_agreement": {"sha256": "x"},
        "groups": ["SMNGRP05", "cosmos77"],
        "final_result": {"winner_group": "cosmos77"},
        "sub_games": [row(1)],
    }


@patch("cosmos77_cop.report.gmail.build_service")
@patch("cosmos77_cop.report.gmail.send_report", return_value={"id": "m1"})
def test_confirmed_counted_send_advances_the_ledger(_send, _build, tmp_path):
    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    path = tmp_path / "result.json"
    path.write_bytes(canonical_bytes(counted_result_body()) + b"\n")
    assert report_cmd(str(path), counted=True, dry_run=False, root=str(tmp_path)) == 0
    ledger = Ledger.load(tmp_path / "artifacts" / "league_ledger.json")
    assert ledger.counted_games_played == 1
    assert ledger.has_played("SMNGRP05")
    assert ledger.entries["SMNGRP05"]["won"] is True


@patch("cosmos77_cop.report.gmail.build_service")
@patch("cosmos77_cop.report.gmail.send_report", return_value={"id": "m2"})
def test_friendly_send_never_touches_the_ledger(_send, _build, tmp_path):
    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    body = {**counted_result_body(), "league": {"counted": False}}
    path = tmp_path / "result.json"
    path.write_bytes(canonical_bytes(body) + b"\n")
    assert report_cmd(str(path), counted=False, dry_run=False, root=str(tmp_path)) == 0
    assert Ledger.load(tmp_path / "artifacts" / "league_ledger.json").counted_games_played == 0


@patch("cosmos77_cop.report.gmail.build_service")
@patch("cosmos77_cop.report.gmail.send_report", return_value={"id": "m3"})
def test_a_double_counted_send_fails_loudly_on_the_ledger(_send, _build, tmp_path, capsys):
    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    ledger = Ledger.load(tmp_path / "artifacts" / "league_ledger.json")
    ledger.record(opponent="SMNGRP05", game_id="g", game_uid="u", won=False, settled_at="t")
    path = tmp_path / "result.json"
    path.write_bytes(canonical_bytes(counted_result_body()) + b"\n")
    assert report_cmd(str(path), counted=True, dry_run=False, root=str(tmp_path)) == 1
    assert "LEDGER ERROR" in capsys.readouterr().out


def test_dry_run_counted_never_advances_the_ledger(tmp_path):
    (tmp_path / "credentials.json").write_text("{}", encoding="utf-8")
    path = tmp_path / "result.json"
    path.write_bytes(canonical_bytes(counted_result_body()) + b"\n")
    assert report_cmd(str(path), counted=True, dry_run=True, root=str(tmp_path)) == 0
    assert Ledger.load(tmp_path / "artifacts" / "league_ledger.json").counted_games_played == 0
