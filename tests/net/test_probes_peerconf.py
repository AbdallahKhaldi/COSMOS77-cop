"""Probe status classification (406=ready) and per-peer config loading with budget checks."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from cosmos77_cop.net.probes import READY, classify_status, probe
from cosmos77_cop.net.receiver import BudgetError
from cosmos77_cop.orchestrator.peerconf import PeerConfig, load_peer_config


def test_status_classification_table():
    assert classify_status(406) == READY
    assert "nothing-behind" in classify_status(502)
    assert "tunnel" in classify_status(421)
    assert "unrouted" in classify_status(530)
    assert "forwarder" in classify_status(301)
    assert "session" in classify_status(400)
    assert classify_status(200) == "unexpected-200"


@patch("cosmos77_cop.net.probes.httpx.get")
def test_probe_classifies_and_survives_unreachable(mock_get):
    mock_get.return_value = MagicMock(status_code=406)
    assert probe("http://x/mcp") == (406, READY)
    mock_get.side_effect = httpx.ConnectError("refused")
    code, kind = probe("http://x/mcp")
    assert code is None and "unreachable" in kind


def test_peerconf_defaults_when_file_absent():
    cfg = load_peer_config(None)
    assert cfg == PeerConfig()


def test_peerconf_overlay_and_budget_refusal(tmp_path):
    good = tmp_path / "peer.toml"
    good.write_text("[network]\nmy_port = 9001\nreorder_window = 6\n")
    cfg = load_peer_config(good)
    assert cfg.my_port == 9001 and cfg.reorder_window == 6
    bad = tmp_path / "bad.toml"
    bad.write_text("[network]\nreorder_window = 0\n")
    with pytest.raises(BudgetError):
        load_peer_config(bad)


def test_gateway_wires_identity_and_uid():
    import json
    from pathlib import Path

    from cosmos77_cop.engine.config import from_dict
    from cosmos77_cop.orchestrator.gateway import Gateway

    repo = Path(__file__).resolve().parents[2]
    raw = json.loads((repo / "config" / "game.json").read_text(encoding="utf-8"))
    gw = Gateway(
        game_cfg=from_dict(raw),
        peer_cfg=PeerConfig(),
        role="police",
        group_id="cosmos77",
        group_name="cosmos77",
        opponent_group_id="rival-team",
    )
    greeting = gw.greeting(nonce="ab" * 16)
    assert greeting["game_uid"].count("-") == 4
    assert greeting["scent_model_sha256"].startswith("81ebee59")
    assert gw.verify(greeting).code == "SPAR-N07"
    thief_view = dict(greeting)
    thief_view["role"] = "thief"
    assert gw.verify(thief_view).ok
