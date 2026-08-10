"""Probe status classification (406=ready) and per-peer config loading with budget checks."""

import dataclasses
import json
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from cosmos77_cop.net.probes import READY, classify_status, probe
from cosmos77_cop.net.receiver import BudgetError
from cosmos77_cop.orchestrator.peerconf import PeerConfig, load_peer_config
from cosmos77_cop.orchestrator.peerlayers import apply_env
from cosmos77_cop.strategy.params import StrategyParams

REPO = Path(__file__).resolve().parents[2]


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


def test_this_machine_has_a_real_peer_toml_that_loads_disarmed():
    """`[league] counted` is unreachable without this file, so `serve --counted` could only
    ever refuse "half-armed" (audit 9a). It is gitignored — it names our ports and the
    opponent's URLs — so nothing in it may be a secret; those live in .env."""
    path = REPO / "config" / "peer.toml"
    assert path.exists(), "config/peer.toml is missing: no counted run can arm on this machine"
    cfg = load_peer_config(path)
    assert cfg.league_counted is False, "arming must stay a deliberate, reviewed edit"
    assert cfg.my_port == 8801 and cfg.opponent_url.endswith("/mcp")
    body = path.read_text(encoding="utf-8")
    for secret in ("GEMINI_API_KEY", "AIza", "password", "passphrase", "api_key", "bearer"):
        assert secret not in body, f"{secret} belongs in .env, never in config/"


def test_the_environment_arms_the_knobs_a_deployed_image_has_no_file_for():
    """The hub clones from GitHub, where peer.toml (gitignored) does not exist — without an
    env path every private knob would silently be its default in production."""
    env = {"COSMOS_TRASH_PROVIDER": "gemini", "COSMOS_TRASH_MODEL": "gemini-3.5-flash-lite",
           "COSMOS_LEAGUE_COUNTED": "true"}
    filled = apply_env({}, env)
    assert filled["trash_talk"] == {"provider": "gemini", "model": "gemini-3.5-flash-lite"}
    assert filled["league"] == {"counted": True}
    assert apply_env({}, {"COSMOS_LEAGUE_COUNTED": "false"})["league"] == {"counted": False}
    assert apply_env({}, {}) == {}


def test_peer_toml_beats_the_environment_when_both_are_present(tmp_path):
    path = tmp_path / "peer.toml"
    path.write_text('[trash_talk]\nprovider = "template"\n', encoding="utf-8")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    assert apply_env(raw, {"COSMOS_TRASH_PROVIDER": "gemini"})["trash_talk"]["provider"] == (
        "template"
    )


def test_the_signed_constitution_overrides_the_private_timeouts(tmp_path):
    """peer.example.toml promises `game.json` wins on parallel keys — rules 6/11 make the
    negotiated response/watchdog deadlines the opponent's entitlement, not our preference."""
    private = tmp_path / "peer.toml"
    private.write_text(
        "[network]\nturn_timeout_seconds = 3\nconnect_timeout_seconds = 2\n"
        "watchdog_seconds = 5\nqueue_depth = 7\n",
        encoding="utf-8",
    )
    cfg = load_peer_config(private, REPO / "config" / "game.json")
    signed = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    assert cfg.turn_timeout_s == signed["network_and_league"]["response_timeout_sec"]
    assert cfg.watchdog_s == signed["network_and_league"]["watchdog_timeout_sec"]
    assert cfg.queue_depth == signed["rate_limiter_gatekeeper"]["queue_depth"]
    assert load_peer_config(private, tmp_path / "absent.json").turn_timeout_s == 3.0


def test_peer_toml_carries_a_strategy_overlay_with_no_restated_defaults(tmp_path):
    """`[strategy]` is plumbed end to end here; only the keys the operator SET travel, so
    strategy/params.py stays the single source of every default."""
    path = tmp_path / "peer.toml"
    path.write_text("[strategy]\nclaim_threshold = 0.75\n", encoding="utf-8")
    assert load_peer_config(path).strategy == {"claim_threshold": 0.75}
    assert load_peer_config(None).strategy == {}
    committed = load_peer_config(REPO / "config" / "peer.toml").strategy
    assert set(committed) <= {f.name for f in dataclasses.fields(StrategyParams)}


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
    # The gid pin (kit E12): value-equal terms from a group that is NOT the configured
    # opponent are refused as a bystander; the real opponent's greeting verifies.
    echoed = gw.verify(thief_view)
    assert echoed.code == "SPAR-N08" and echoed.bystander
    thief_view["group_id"] = "rival-team"
    thief_view["identity"] = {**thief_view["identity"], "group_id": "rival-team"}
    assert gw.verify(thief_view).ok
