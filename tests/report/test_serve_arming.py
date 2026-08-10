"""Run-side counted arming: private peer-layer switch, double arming, live-read counts."""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from cosmos77_cop.arming import ArmingError, declared_count, serve_posture
from cosmos77_cop.orchestrator.peerconf import load_peer_config
from cosmos77_cop.report.ledger import Ledger

REPO = Path(__file__).resolve().parents[2]


def test_peer_layer_carries_the_private_league_switch(tmp_path):
    silent = tmp_path / "silent.toml"
    silent.write_text("[network]\nmy_port = 8801\n", encoding="utf-8")
    assert load_peer_config(silent).league_counted is False
    armed = tmp_path / "armed.toml"
    armed.write_text("[league]\ncounted = true\n", encoding="utf-8")
    assert load_peer_config(armed).league_counted is True
    assert load_peer_config(None).league_counted is False


@patch("cosmos77_cop.arming.has_credentials", return_value=True)
def test_half_armed_serve_refuses_at_startup(_creds):
    for config, cli in ((True, False), (False, True)):
        with pytest.raises(ArmingError, match="half-armed"):
            serve_posture(config_counted=config, cli_counted=cli)


@patch("cosmos77_cop.arming.has_credentials", return_value=False)
def test_fully_armed_refuses_without_a_deliverable_report(_creds):
    with pytest.raises(ArmingError, match="deliver"):
        serve_posture(config_counted=True, cli_counted=True)


@patch("cosmos77_cop.arming.is_dirty", return_value=False)
@patch("cosmos77_cop.arming.has_credentials")
def test_postures_resolve_like_the_mail_side(creds, _dirty):
    creds.return_value = True
    armed = serve_posture(config_counted=True, cli_counted=True)
    assert armed.counted and armed.label == "counted"
    creds.return_value = False
    friendly = serve_posture(config_counted=False, cli_counted=False)
    assert friendly.label == "friendly" and not friendly.counted


@patch("cosmos77_cop.arming.has_credentials", return_value=True)
def test_a_counted_run_refuses_a_dirty_working_tree(_creds):
    """Rule 53: step-0 seals `git rev-parse HEAD`. Playing uncommitted code under that commit
    declares a version that is not the one playing — the friendly path is unaffected."""
    with patch("cosmos77_cop.arming.is_dirty", return_value=True) as dirty:
        with pytest.raises(ArmingError, match="rule 53"):
            serve_posture(config_counted=True, cli_counted=True)
        assert dirty.called
        assert serve_posture(config_counted=False, cli_counted=False).label == "friendly"
    with patch("cosmos77_cop.arming.is_dirty", return_value=False):
        assert serve_posture(config_counted=True, cli_counted=True).counted


@patch("cosmos77_cop.arming.is_dirty", return_value=False)
@patch("cosmos77_cop.arming.has_credentials", return_value=True)
def test_the_committed_peer_layer_can_actually_arm_a_counted_run(_creds, _dirty, tmp_path):
    """The league-blocking check: this machine's real peer.toml, with `counted = true`, ARMS
    instead of refusing half-armed. Nothing is played and nothing is sent."""
    armed = tmp_path / "peer.toml"
    body = (REPO / "config" / "peer.toml").read_text(encoding="utf-8")
    armed.write_text(re.sub(r"(?m)^counted\s*=.*$", "counted = true", body), encoding="utf-8")
    cfg = load_peer_config(armed)
    assert cfg.league_counted is True
    posture = serve_posture(
        config_counted=cfg.league_counted, cli_counted=True, opponent="never-met",
        root=str(tmp_path),
    )
    assert posture.counted and posture.label == "counted"
    with pytest.raises(ArmingError, match="half-armed"):
        serve_posture(config_counted=cfg.league_counted, cli_counted=False, root=str(tmp_path))


def test_declared_count_is_live_read_from_the_ledger(tmp_path):
    assert declared_count(str(tmp_path)) == 0
    ledger = Ledger.load(tmp_path / "artifacts" / "league_ledger.json")
    ledger.record(opponent="zulu", game_id="g", game_uid="u", won=True, settled_at="t")
    assert declared_count(str(tmp_path)) == 1
