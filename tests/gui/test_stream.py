"""The per-turn JSONL event sink: exact line shape, append-only, absolute fault isolation."""

import json
import types

from cosmos77_cop.gui.attach import ViewAttachment
from cosmos77_cop.gui.model import LiveView
from cosmos77_cop.gui.stream import EVENTS_FILENAME, EventSink

EXPECTED_KEYS = {
    "t", "role", "sub_game", "step", "banner", "self_pos", "barriers",
    "barriers_left", "posterior", "perceived_scent", "confidence", "hints",
}


def view(step=1, banner="YOUR TURN"):
    return LiveView(
        grid_size=7,
        role="police",
        self_pos=(2, 3),
        barriers=frozenset({(1, 1), (0, 5)}),
        posterior={(3, 3): 0.75, (3, 4): 0.25},
        perceived_scent={(3, 3): 0.9},
        banner=banner,
        step=step,
        sub_game=2,
        hints=("the north bridges are ours",),
        confidence="fuzzy",
        barriers_left=11,
    )


def test_sink_appends_one_exact_json_line_per_update(tmp_path):
    sink = EventSink(tmp_path)
    sink.update(view(step=1))
    sink.update(view(step=2, banner="LOCKED"))
    lines = (tmp_path / EVENTS_FILENAME).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first, second = (json.loads(line) for line in lines)
    assert set(first) == EXPECTED_KEYS
    assert first["t"] == "view" and first["role"] == "police"
    assert first["self_pos"] == [2, 3]
    assert first["barriers"] == [[0, 5], [1, 1]]
    assert first["posterior"] == {"3,3": 0.75, "3,4": 0.25}
    assert first["perceived_scent"] == {"3,3": 0.9}
    assert first["hints"] == ["the north bridges are ours"]
    assert first["barriers_left"] == 11 and first["confidence"] == "fuzzy"
    assert (first["banner"], second["banner"]) == ("YOUR TURN", "LOCKED")
    assert (first["step"], second["step"]) == (1, 2)
    assert first["sub_game"] == 2
    assert sink.errors == 0


def test_sink_swallows_and_counts_every_fault(tmp_path):
    blocked = EventSink(tmp_path)
    blocked.path.mkdir(parents=True)  # the target path is now a directory, not a writable file
    blocked.update(view())
    assert blocked.errors == 1
    broken = EventSink(tmp_path / "ok")
    broken.update(types.SimpleNamespace())  # not a LiveView at all — still must not raise
    assert broken.errors == 1
    assert not (tmp_path / "ok" / EVENTS_FILENAME).exists()


def test_attachment_feeds_the_extra_sink_without_a_window(tmp_path):
    sink = EventSink(tmp_path)
    bridge = types.SimpleNamespace()
    attachment = ViewAttachment(extra=sink)
    attachment.attach(bridge, 3)
    state = types.SimpleNamespace(
        cfg=types.SimpleNamespace(grid_size=7), role="police", my_pos=(0, 0),
        board=types.SimpleNamespace(barriers=set()), barriers_left=14,
    )
    kit = types.SimpleNamespace(
        tracker=types.SimpleNamespace(estimate=lambda: (None, "none")),
        flow=types.SimpleNamespace(received={}),
    )
    bridge.on_view(state, kit, "LOCKED", 4)
    line = json.loads((tmp_path / EVENTS_FILENAME).read_text(encoding="utf-8"))
    assert line["sub_game"] == 3 and line["step"] == 4 and line["banner"] == "LOCKED"
    assert line["posterior"] == {} and line["confidence"] == "none"


def test_attachment_without_any_sink_stays_a_noop():
    bridge = types.SimpleNamespace()
    ViewAttachment(extra=None).attach(bridge, 1)
    assert not hasattr(bridge, "on_view")
