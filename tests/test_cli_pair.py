"""The ``pair`` subcommand: the console pairing packet as machine-readable stdout JSON."""

import json
from pathlib import Path

from cosmos77_cop.cli import main
from cosmos77_cop.console.pairing import build_packet
from cosmos77_cop.orchestrator.identity import TEAM_REPOS

REPO = Path(__file__).resolve().parents[1]
RAW = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))


def test_pair_prints_the_exact_console_packet_as_json(capsys):
    rc = main([
        "pair", "--opponent", "zulu", "--their-cop", "https://z/cop/mcp",
        "--their-thief", "https://z/thief/mcp", "--our-cop", "https://u/cop/mcp",
        "--our-thief", "https://u/thief/mcp",
    ])
    assert rc == 0
    packet = json.loads(capsys.readouterr().out)
    expected = build_packet(
        RAW, opponent="zulu", our_cop="https://u/cop/mcp", our_thief="https://u/thief/mcp",
        their_cop="https://z/cop/mcp", their_thief="https://z/thief/mcp",
    ).as_dict()
    assert packet == expected
    assert packet["game_id"] == "cosmos77-vs-zulu"
    assert packet["windows"][0]["window"] == "g1" and "message" in packet


def test_pair_defaults_leave_placeholders_for_our_urls(capsys):
    rc = main(["pair", "--opponent", "zulu", "--their-cop", "c", "--their-thief", "t"])
    assert rc == 0
    packet = json.loads(capsys.readouterr().out)
    assert "(our cop MCP URL)" in packet["message"]
    assert "(our thief MCP URL)" in packet["message"]


def test_pair_message_states_the_true_repo_links_from_either_half(capsys):
    """Regression: the hub shells EITHER repo for this packet, and the repo links must be the
    shared identity constants — a token-swapped literal once inverted them in one half."""
    main(["pair", "--opponent", "zulu", "--their-cop", "c", "--their-thief", "t"])
    message = json.loads(capsys.readouterr().out)["message"]
    assert f"cop   {TEAM_REPOS['cop']}" in message
    assert f"thief {TEAM_REPOS['thief']}" in message
