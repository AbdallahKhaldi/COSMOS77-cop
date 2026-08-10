"""A5: Gemini is constructed only when CONFIGURED and KEYED, and we declare what we ran.

``identity.LLM_MODEL`` used to be stamped into the sealed step-0 record and the pre-game
declaration while no runtime path ever constructed a client — a false declaration, and rules
37-38 make those project-fatal.
"""

from cosmos77_cop.engine.config import load_game_config
from cosmos77_cop.hints.gemini import API_MIN_TIMEOUT_S
from cosmos77_cop.orchestrator.hintconf import TEMPLATE, HintSetup, hint_setup
from cosmos77_cop.orchestrator.peerconf import PeerConfig
from cosmos77_cop.orchestrator.series import SeriesDriver
from cosmos77_cop.orchestrator.turnstate import SideKit

CFG = load_game_config("config/game.json")
MODEL = "gemini-3.5-flash-lite"


def kit(setup):
    return SideKit.fresh(CFG, "police", seed=7, setup=setup)


def test_template_provider_never_builds_a_client_even_with_a_key():
    setup = HintSetup("template", MODEL, "a-key", 12.0)
    assert kit(setup).hints.gemini is None
    assert setup.declared_model == TEMPLATE


def test_gemini_without_a_key_falls_back_to_templates_and_declares_template():
    setup = HintSetup("gemini", MODEL, None, 12.0)
    assert kit(setup).hints.gemini is None
    assert setup.declared_model == TEMPLATE


def test_gemini_with_a_key_is_wired_and_declared_by_its_real_name():
    setup = HintSetup("gemini", MODEL, "a-key", 12.0)
    hinter = kit(setup).hints.gemini
    assert hinter is not None
    assert hinter.model == MODEL and hinter.api_key == "a-key"
    assert hinter.timeout_s >= API_MIN_TIMEOUT_S, "a sub-floor deadline is a 400, not speed"
    assert setup.declared_model == MODEL


def test_the_negotiated_series_budget_reaches_the_provider():
    provider = kit(HintSetup("gemini", MODEL, "k", 12.0)).hints
    assert provider.token_budget == CFG.token_budget_per_series == 200000


def test_hint_setup_reads_the_private_peer_config(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=abc\n", encoding="utf-8")
    setup = hint_setup(PeerConfig(trash_provider="gemini", trash_model=MODEL), env_path=env)
    assert setup == HintSetup("gemini", MODEL, "abc", 12.0)
    assert hint_setup(PeerConfig(), env_path=env).declared_model == TEMPLATE


def test_the_driver_declares_the_model_it_actually_runs(tmp_path):
    driver = SeriesDriver(
        game_cfg=CFG, peer_cfg=PeerConfig(), gid_a="cosmos77", gid_b="zulu",
        out_dir=tmp_path, code_version="a" * 40,
    )
    assert driver.hints.declared_model == TEMPLATE
    assert driver.gateway_for(1).identity["llm_model"] == TEMPLATE
    assert driver.tokens_spent == 0


def test_a_sub_floor_timeout_is_clamped_instead_of_silently_disabling_gemini():
    """5 s (the value shipped before A5) is refused by the endpoint on EVERY call."""
    hinter = kit(HintSetup("gemini", MODEL, "k", 5.0)).hints.gemini
    assert hinter.timeout_s == API_MIN_TIMEOUT_S
