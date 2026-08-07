"""The view attachment (observation only) and the CLI command layer, headless."""

import inspect
import json
import types
from pathlib import Path
from unittest.mock import patch

from cosmos77_cop.belief.bayes import BeliefMap
from cosmos77_cop.commands import compare_cmd, doctor_cmd, kill_cmd, replay_cmd
from cosmos77_cop.engine.board import Board
from cosmos77_cop.gui.attach import ViewAttachment
from cosmos77_cop.protocol.sealing import build_turn_payload, commit


def fake_state():
    return types.SimpleNamespace(
        cfg=types.SimpleNamespace(grid_size=7),
        role="police",
        my_pos=(2, 2),
        board=Board(7, {(1, 1)}),
        barriers_left=11,
    )


def fake_kit():
    return types.SimpleNamespace(
        tracker=types.SimpleNamespace(estimate=lambda: (None, "fuzzy")),
        flow=types.SimpleNamespace(received={"3,3": 0.9}),
    )


def test_attachment_is_a_noop_without_sinks():
    bridge = types.SimpleNamespace()
    ViewAttachment().attach(bridge, 1)
    assert not hasattr(bridge, "on_view")


def test_attachment_writes_snapshots_only_at_the_named_steps(tmp_path):
    bridge = types.SimpleNamespace(belief=BeliefMap(Board(7), (0, 0)))
    attachment = ViewAttachment(snapshot_dir=tmp_path, snapshot_steps=(2,))
    attachment.attach(bridge, 4)
    attachment.note_hint("the north bridges are ours")
    bridge.on_view(fake_state(), fake_kit(), "YOUR TURN", 1)
    assert list(tmp_path.glob("*.svg")) == []
    bridge.on_view(fake_state(), fake_kit(), "YOUR TURN", 2)
    written = list(tmp_path.glob("*.svg"))
    assert len(written) == 1
    assert written[0].name == "live_g04_step02_fuzzy.svg"
    svg = written[0].read_text(encoding="utf-8")
    assert "north bridges" in svg and "sub-game 4" in svg


def test_attachment_pushes_to_a_window_without_a_display():
    seen = []
    window = types.SimpleNamespace(update=seen.append)
    bridge = types.SimpleNamespace(belief=BeliefMap(Board(7), (0, 0)))
    attachment = ViewAttachment(window=window)
    attachment.attach(bridge, 2)
    bridge.on_view(fake_state(), fake_kit(), "LOCKED", 5)
    assert len(seen) == 1
    assert seen[0].banner == "LOCKED" and seen[0].sub_game == 2


def write_log(tmp_path, tamper=False):
    payload = build_turn_payload(
        step=1, role="thief", sub_game=1, grid_size=7, self_pos=(3, 3), barriers=[],
        move="MOVE:S", intent="truth", hint="quiet night", verdict="moved",
    )
    nonce = "ab" * 16
    record = {"payload": payload, "nonce": nonce, "commit": commit(payload, nonce)}
    if tamper:
        record["payload"]["hint"] = "loud night"
    path = tmp_path / "log_x_g01.json"
    path.write_text(json.dumps({"records": [record], "opponent_records": []}), encoding="utf-8")
    return path


def test_replay_cmd_clean_and_tampered(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("COSMOS_NO_GUI", "1")
    (tmp_path / "a").mkdir()
    clean = write_log(tmp_path / "a", tamper=False)
    assert replay_cmd(str(clean), expect_clean=True) == 0
    assert "Verified OK" in capsys.readouterr().out
    (tmp_path / "b").mkdir()
    bad = write_log(tmp_path / "b", tamper=True)
    assert replay_cmd(str(bad), expect_clean=True) == 1
    assert "TAMPERED" in capsys.readouterr().out


def test_replay_cmd_writes_both_stamps(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("COSMOS_NO_GUI", "1")
    (tmp_path / "b").mkdir()
    bad = write_log(tmp_path / "b", tamper=True)
    replay_cmd(str(bad), screenshot_dir=str(tmp_path / "img"))
    names = {p.name for p in (tmp_path / "img").glob("*.svg")}
    assert names == {"replay_verified.svg", "replay_tampered.svg"}
    assert "TAMPERED" in (tmp_path / "img" / "replay_tampered.svg").read_text(encoding="utf-8")


def test_compare_cmd_passes_and_reports(tmp_path, capsys):
    body = {"game_id": "a-vs-b", "sub_games": [], "final_result": {}, "mutual_agreement": {}}
    ours = tmp_path / "ours.json"
    theirs = tmp_path / "theirs.json"
    ours.write_text(json.dumps(body), encoding="utf-8")
    theirs.write_text(json.dumps(body), encoding="utf-8")
    assert compare_cmd(str(ours), str(theirs)) == 0
    assert "PASS" in capsys.readouterr().out
    theirs.write_text(json.dumps({**body, "game_id": "x-vs-y"}), encoding="utf-8")
    assert compare_cmd(str(ours), str(theirs)) == 1
    assert "MISMATCH" in capsys.readouterr().out


def test_kill_and_doctor_report_without_touching_the_network(capsys):
    with patch("cosmos77_cop.commands.subprocess.run") as run:
        assert kill_cmd() == 0
        assert run.called
    assert "freed tcp:" in capsys.readouterr().out
    monkey = Path("config/game.json")
    assert monkey.exists()
    assert doctor_cmd() == 0
    out = capsys.readouterr().out
    assert "constitution loads" in out and "GEMINI_API_KEY" in out


def test_sibling_is_derived_from_our_directory_not_our_role():
    """Regression: the repos are kept in sync by a token swap, and a ROLE-based branch inverts
    under it — which made selfplay spawn a second peer of our own role in our own directory."""
    from cosmos77_cop.commands import OUR_REPO, SIBLING_REPO, SIBLING_TOOL

    assert SIBLING_REPO != OUR_REPO
    assert {OUR_REPO, SIBLING_REPO} == {"COSMOS77-cop", "COSMOS77-thief"}
    assert "cosmos-" + SIBLING_REPO.rsplit("-", 1)[-1] == SIBLING_TOOL
    assert f"cosmos-{OUR_REPO.rsplit('-', 1)[-1]}" != SIBLING_TOOL


def test_zeroed_windows_never_report_a_green_series(tmp_path):
    """A settled technical-loss row is reportable, but a gate must not read it as a played game."""

    from cosmos77_cop import commands
    from cosmos77_cop.protocol.outcome import ZEROED

    assert "technical_loss" in ZEROED and "timeout" in ZEROED
    source = inspect.getsource(commands.serve_cmd)
    assert "zeroed" in source and "return 6" in source
