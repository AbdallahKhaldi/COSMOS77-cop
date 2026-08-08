"""The console: correct pairing derivations, and the rails that keep it legal."""

import json
from pathlib import Path

import pytest

from cosmos77_cop.console.page import page_html
from cosmos77_cop.console.pairing import build_packet, window_map
from cosmos77_cop.console.server import build_command
from cosmos77_cop.console.state import COUNTED_REFUSAL, Runner, readiness
from cosmos77_cop.protocol.ids import game_uid
from cosmos77_cop.protocol.terms import terms_from_config

REPO = Path(__file__).resolve().parents[2]
RAW = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))


def test_uid_matches_the_protocol_derivation_exactly():
    """The console must derive the SAME uid the wire does — from the flat terms, not the config."""
    packet = build_packet(RAW, opponent="team-bet", our_cop="c", our_thief="t")
    assert packet.game_uid == game_uid(terms_from_config(RAW), "cosmos77", "team-bet")
    assert packet.game_uid != game_uid(RAW, "cosmos77", "team-bet")


def test_game_id_sorts_the_pair_either_way():
    a = build_packet(RAW, opponent="aardvark", our_cop="c", our_thief="t")
    z = build_packet(RAW, opponent="zulu", our_cop="c", our_thief="t")
    assert a.game_id == "aardvark-vs-cosmos77"
    assert z.game_id == "cosmos77-vs-zulu"


def test_window_map_alternates_and_dials_the_complementary_role():
    rows = window_map("zulu", "our-cop", "our-thief", "their-cop", "their-thief")
    assert [r["us"] for r in rows] == ["cop", "thief", "cop", "thief", "cop", "thief"]
    assert rows[0]["we_dial"] == "their-thief" and rows[0]["they_dial"] == "our-cop"
    assert rows[1]["we_dial"] == "their-cop" and rows[1]["they_dial"] == "our-thief"
    later = window_map("aardvark", "our-cop", "our-thief", "their-cop", "their-thief")
    assert [r["us"] for r in later] == ["thief", "cop", "thief", "cop", "thief", "cop"]


def test_message_states_everything_a_pairing_must_agree():
    packet = build_packet(
        RAW, opponent="team-bet", our_cop="https://a/mcp", our_thief="https://b/mcp"
    )
    for token in (
        "thief moves first",
        "series_add",
        "subtractive_chebyshev_v1",
        "PER SERIES",
        packet.game_uid,
        packet.game_id,
        "T-protocol",
    ):
        assert token in packet.message


def test_console_can_never_arm_a_counted_run(tmp_path):
    runner = Runner(tmp_path)
    with pytest.raises(PermissionError, match="never be armed"):
        runner.start("sneaky", ["uv", "run", "cosmos-cop", "report", "x.json", "--counted"])
    assert runner.current is None
    assert "rules 37-38" in COUNTED_REFUSAL


def test_buttons_map_to_safe_commands():
    _, selfplay = build_command(REPO, "selfplay", "", "")
    assert selfplay[2:] == ["cosmos-cop", "selfplay", "--windows", "6"]
    label, f1 = build_command(REPO, "f1", "https://them/mcp", "them")
    assert "--windows" in f1 and f1[f1.index("--windows") + 1] == "1"
    assert "--counted" not in f1 and "them" in label
    _, f2 = build_command(REPO, "f2", "https://them/mcp", "them")
    assert f2[f2.index("--windows") + 1] == "6"
    _, blank_peer = build_command(REPO, "f2", "", "them")
    assert "selfplay" in blank_peer, "no peer URL must never dial a stranger"


def test_page_shows_operations_only_never_a_board():
    html = page_html()
    assert "Challenge console" in html
    for forbidden in ("belief", "heatmap", "posterior", "opponent position"):
        assert forbidden not in html.lower()
    assert "Counted games are not here on purpose" in html


def test_readiness_reports_every_local_prerequisite(tmp_path):
    rows = readiness(tmp_path)
    labels = {r["label"] for r in rows}
    assert {"Gmail client", "Gmail consent", "Gemini key", "constitution present"} <= labels
    assert all(isinstance(r["ok"], bool) for r in rows)
    live = readiness(REPO)
    assert next(r for r in live if r["label"] == "constitution present")["ok"]
