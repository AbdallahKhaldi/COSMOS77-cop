"""The peer.toml [strategy] overlay: applied for real, and never silently dropped."""

from __future__ import annotations

import pytest

from cosmos77_cop.strategy.params import StrategyParams, from_overlay


def test_an_empty_overlay_is_exactly_the_defaults():
    assert from_overlay({}) == StrategyParams()


def test_only_the_named_keys_move():
    tuned = from_overlay({"reserve_barriers": 5})
    assert tuned.reserve_barriers == 5
    assert tuned.claim_threshold == StrategyParams().claim_threshold


def test_every_documented_knob_actually_reaches_the_params():
    overlay = {"claim_threshold": 0.75, "reserve_barriers": 4,
               "taboo_distance": 2, "escape_horizon": 5, "place_range": 1}
    assert from_overlay(overlay) == StrategyParams(**overlay)


def test_an_unknown_key_is_refused_rather_than_ignored():
    """A dropped knob would make peer.toml describe a run that never happened."""
    with pytest.raises(ValueError, match="unknown key"):
        from_overlay({"reserve_barriers": 4, "reserve_barrier": 9})


def test_the_series_hands_the_overlay_to_the_brain():
    """The wiring itself is the deliverable: plumbing that stops short is documentation."""
    import inspect

    from cosmos77_cop.orchestrator import series

    assert "BrainBridge(state, self.peer_cfg.strategy_params())" in inspect.getsource(series)


def test_a_peer_config_turns_its_own_overlay_into_typed_knobs():
    from cosmos77_cop.orchestrator.peerconf import PeerConfig

    assert PeerConfig(strategy={"place_range": 2}).strategy_params().place_range == 2
    assert PeerConfig().strategy_params() == StrategyParams()


def test_loading_a_peer_file_with_a_mistyped_knob_refuses_at_load(tmp_path):
    """Before a port is bound -- not once a counted series is already in flight."""
    from cosmos77_cop.orchestrator.peerconf import load_peer_config

    path = tmp_path / "peer.toml"
    path.write_text("[strategy]\nreserve_barrier = 9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown key"):
        load_peer_config(path, game_config_path=tmp_path / "absent.json")
