"""Rule-37 truthfulness: the greeting identity block declares the live counted-game count."""

from cosmos77_cop.engine.config import load_game_config
from cosmos77_cop.orchestrator.gateway import Gateway
from cosmos77_cop.orchestrator.peerconf import PeerConfig
from cosmos77_cop.orchestrator.series import SeriesDriver

CFG = load_game_config("config/game.json")


def gateway(**kwargs):
    return Gateway(
        game_cfg=CFG, peer_cfg=PeerConfig(), role="police",
        group_id="cosmos77", group_name="cosmos77", **kwargs,
    )


def test_gateway_identity_declares_the_counted_count():
    gw = gateway(counted_games_played=2)
    assert gw.identity["counted_games_played"] == 2
    greeting = gw.greeting(nonce="0" * 32)
    assert greeting["identity"]["counted_games_played"] == 2


def test_gateway_identity_omits_an_undeclared_count():
    assert "counted_games_played" not in gateway().identity


def test_series_driver_threads_the_count_into_every_window(tmp_path):
    driver = SeriesDriver(
        game_cfg=CFG, peer_cfg=PeerConfig(), gid_a="cosmos77", gid_b="zulu",
        out_dir=tmp_path, code_version="a" * 40, num_games_declared=3,
    )
    assert driver.gateway_for(1).identity["counted_games_played"] == 3
    assert driver.gateway_for(2).identity["counted_games_played"] == 3


def test_public_mcp_url_env_overrides_the_loopback_identity(monkeypatch):
    public = "https://cosmos77-arena-production.up.railway.app/cop/mcp"
    monkeypatch.setenv("COSMOS_PUBLIC_MCP_URL", public)
    assert gateway().identity["mcp_servers"]["self"] == public
    monkeypatch.delenv("COSMOS_PUBLIC_MCP_URL")
    assert gateway().identity["mcp_servers"]["self"].startswith("http://127.0.0.1:")
