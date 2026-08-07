"""The live view is LOCAL TRUTH ONLY (rules 8-9) — and is structurally unable to be otherwise."""

import inspect
import types

from cosmos77_cop import gui
from cosmos77_cop.belief.bayes import BeliefMap
from cosmos77_cop.engine.board import Board
from cosmos77_cop.gui import live, model, render
from cosmos77_cop.gui.model import LOCKED, YOUR_TURN, HintTicker, LiveView, build_view


def fake_state(pos=(2, 2), barriers=((1, 1),)):
    cfg = types.SimpleNamespace(grid_size=7)
    board = Board(7, set(barriers))
    return types.SimpleNamespace(
        cfg=cfg, role="police", my_pos=pos, board=board, barriers_left=11, sub_game=3
    )


def fake_kit(confidence="fuzzy", cell=None, received=None):
    tracker = types.SimpleNamespace(estimate=lambda: (cell, confidence))
    flow = types.SimpleNamespace(received=received or {})
    return types.SimpleNamespace(tracker=tracker, flow=flow)


def test_exact_tracking_renders_as_a_belief_of_one_not_a_position():
    view = build_view(
        fake_state(), fake_kit("exact", (5, 5)), object(), banner=YOUR_TURN, step=4
    )
    assert view.posterior == {(5, 5): 1.0}
    assert view.belief_peak == ((5, 5), 1.0)
    assert "inferred" in view.caption and "not a bird" in view.caption


def test_fuzzy_mode_renders_the_spread_posterior():
    bridge = types.SimpleNamespace(belief=BeliefMap(Board(7), (0, 0)))
    bridge.belief.diffuse()
    view = build_view(fake_state(), fake_kit(), bridge, banner=LOCKED, step=2)
    assert len(view.posterior) == 3
    assert sum(view.posterior.values()) == 1.0
    assert "physics" in view.caption


def test_view_carries_only_locally_known_facts():
    fields = set(LiveView.__dataclass_fields__)
    forbidden = {"opponent_pos", "thief_pos", "cop_pos", "true_pos", "objective_board"}
    assert not fields & forbidden


def test_no_gui_module_can_reach_the_opponents_true_state():
    """The build seam takes (state, kit, bridge) — none of which holds the rival's position."""
    signature = inspect.signature(build_view)
    assert list(signature.parameters)[:3] == ["state", "kit", "bridge"]
    for module in (model, render, live, gui):
        source = inspect.getsource(module)
        assert "opponent_pos" not in source
        assert "rival_pos" not in source


def test_hint_ticker_keeps_the_last_few():
    ticker = HintTicker(limit=3)
    for hint in ["a", "", "b", "c", "d"]:
        current = ticker.push(hint)
    assert current == ("b", "c", "d")
