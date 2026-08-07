"""Replay verification (rule 20): a clean log stamps Verified OK, a flipped byte TAMPERED."""

import json

from cosmos77_cop.gui.model import LiveView
from cosmos77_cop.gui.render import live_svg
from cosmos77_cop.protocol.sealing import build_turn_payload, commit
from cosmos77_cop.replay.render import step_svg, summary_line
from cosmos77_cop.replay.verify import TAMPERED, VERIFIED, verify_log, verify_records
from cosmos77_cop.replay.viewer import ReplayViewer, open_log


def record(step, pos, hint="calm streets"):
    payload = build_turn_payload(
        step=step, role="thief", sub_game=1, grid_size=7, self_pos=pos, barriers=[],
        move="MOVE:S", intent="truth", hint=hint, verdict="moved",
    )
    nonce = f"{step:032x}"
    return {"payload": payload, "nonce": nonce, "commit": commit(payload, nonce)}


def write_log(tmp_path, records, opponent=()):
    log = {
        "summary": {"result": "survival"},
        "records": records,
        "opponent_records": list(opponent),
    }
    path = tmp_path / "log_x_g01.json"
    path.write_text(json.dumps(log), encoding="utf-8")
    return path


def test_clean_log_verifies_every_record(tmp_path):
    path = write_log(tmp_path, [record(1, (3, 3)), record(2, (4, 3))], [record(1, (0, 0))])
    result = verify_log(path)
    assert result.clean
    assert result.stamp == VERIFIED
    assert len(result.verdicts) == 3
    assert [v.side for v in result.verdicts] == ["ours", "ours", "opponent"]
    assert "3/3 records re-hashed" in summary_line(result)


def test_one_flipped_byte_stamps_tampered(tmp_path):
    records = [record(1, (3, 3)), record(2, (4, 3))]
    records[1]["payload"]["hint"] = "calm streets!"
    path = write_log(tmp_path, records)
    result = verify_log(path)
    assert not result.clean
    assert result.stamp == TAMPERED
    failed = result.failures
    assert len(failed) == 1
    assert failed[0].step == 2
    assert failed[0].declared != failed[0].recomputed
    assert "TAMPERED" in summary_line(result)


def test_hebrew_and_emoji_survive_the_round_trip(tmp_path):
    path = write_log(tmp_path, [record(1, (3, 3), hint="אני ליד הכיכר 🙂")])
    assert verify_log(path).clean


def test_a_simplified_nonce_pipe_move_commit_is_caught(tmp_path):
    """The book's own shorthand does not reproduce a real commit — the viewer must catch it."""
    import hashlib

    rec = record(1, (3, 3))
    rec["commit"] = hashlib.sha256(f"{rec['nonce']}|{rec['payload']['move']}".encode()).hexdigest()
    assert not verify_log(write_log(tmp_path, [rec])).clean


def test_viewer_steps_and_clamps(tmp_path):
    path = write_log(tmp_path, [record(1, (3, 3)), record(2, (4, 3)), record(3, (4, 4))])
    viewer = open_log(path)
    assert isinstance(viewer, ReplayViewer)
    assert viewer.step(-5) == 0
    assert viewer.step(1) == 1
    assert viewer.step(99) == 2
    assert viewer.current().step == 3


def test_renderers_emit_wellformed_svg(tmp_path):
    path = write_log(tmp_path, [record(1, (3, 3)), record(2, (4, 3))])
    result = verify_log(path)
    svg = step_svg(result, result.verdicts[0])
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert VERIFIED in svg
    view = LiveView(
        grid_size=7, role="police", self_pos=(0, 0), barriers=frozenset({(1, 1)}),
        posterior={(5, 5): 1.0}, perceived_scent={(4, 4): 0.6}, banner="YOUR TURN",
        step=3, sub_game=1, hints=("watch the north bridges",), confidence="exact",
    )
    live = live_svg(view)
    assert live.startswith("<svg") and "YOUR TURN" in live
    assert "not a bird" in live


def test_verify_records_skips_malformed_entries():
    assert verify_records([{"nonce": "x"}, {"payload": "nope"}], "ours") == []
