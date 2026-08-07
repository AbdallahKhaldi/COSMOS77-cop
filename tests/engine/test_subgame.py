"""Referee behavior: turn order, endings, quota, scoring rows (rules 46-48)."""

import json
from pathlib import Path

import pytest

from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.engine.rules import IllegalMoveError
from cosmos77_cop.engine.subgame import POLICE, THIEF, SubGame, TurnError, score_for

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_game(**overrides) -> SubGame:
    raw = json.loads((REPO_ROOT / "config" / "game.json").read_text(encoding="utf-8"))
    for dotted, value in overrides.items():
        section, key = dotted.split(".")
        raw[section][key] = value
    return SubGame(from_dict(raw))


def test_thief_moves_first_and_turns_alternate():
    g = make_game()
    with pytest.raises(TurnError, match="thief's turn"):
        g.move(POLICE, "S")
    g.move(THIEF, "N")
    with pytest.raises(TurnError, match="police's turn"):
        g.move(THIEF, "N")
    g.move(POLICE, "S")
    assert g.mover == THIEF


def test_survival_after_35_thief_moves_cop_gets_34():
    g = make_game()
    for _ in range(34):
        g.move(THIEF, "STAY")
        g.move(POLICE, "STAY")
    assert not g.over
    g.move(THIEF, "STAY")
    assert g.over
    assert g.outcome.result == "survival"
    assert g.outcome.winner_role == THIEF
    assert g.outcome.steps == 35
    assert g.moves_made[POLICE] == 34
    with pytest.raises(TurnError, match="already ended"):
        g.move(POLICE, "STAY")


def test_co_location_capture_ends_immediately():
    g = make_game(**{"board_and_agents.cop_start": [3, 2]})
    g.move(THIEF, "W")
    assert g.over
    assert g.outcome.result == "capture"
    assert g.outcome.capture_family == "co_location"
    assert g.outcome.winner_role == POLICE


def test_barrier_placement_consumes_turn_and_quota():
    g = make_game()
    g.move(THIEF, "N")
    g.place_barrier((0, 1))
    assert g.mover == THIEF
    assert g.barriers_left == 13
    assert (0, 1) in g.board.barriers
    g.move(THIEF, "S")
    with pytest.raises(IllegalMoveError, match="not the cop's cell"):
        g.place_barrier((5, 5))


def test_barrier_quota_exhaustion_refused():
    g = make_game()
    g.barriers_left = 0
    g.move(THIEF, "STAY")
    with pytest.raises(IllegalMoveError, match="quota exhausted"):
        g.place_barrier((0, 1))


def test_rule46_barrier_on_thief_cell_captures():
    g = make_game(**{"board_and_agents.cop_start": [1, 3]})
    g.move(THIEF, "N")
    g.place_barrier((2, 3))
    assert g.over
    assert g.outcome.capture_family == "rule_46"


def test_rule47_via_real_boxing_sequence():
    g = make_game(**{"board_and_agents.cop_start": [1, 1], "board_and_agents.thief_start": [0, 0]})
    g.move(THIEF, "STAY")
    g.place_barrier((0, 1))
    g.move(THIEF, "STAY")
    g.place_barrier((1, 0))
    assert g.over
    assert g.outcome.result == "capture"
    assert g.outcome.capture_family == "rule_47"


def test_settle_produces_zeroed_sanction_row():
    g = make_game()
    out = g.settle("timeout")
    assert out.winner_role is None
    assert score_for(out, g.cfg) == {POLICE: 0, THIEF: 0}
    with pytest.raises(ValueError, match="zeroed"):
        make_game().settle("capture")


def test_scoring_rows_match_fixed_table():
    g = make_game(**{"board_and_agents.cop_start": [3, 2]})
    g.move(THIEF, "W")
    assert score_for(g.outcome, g.cfg) == {POLICE: 20, THIEF: 5}
    s = make_game()
    for _ in range(34):
        s.move(THIEF, "STAY")
        s.move(POLICE, "STAY")
    s.move(THIEF, "STAY")
    assert score_for(s.outcome, s.cfg) == {POLICE: 5, THIEF: 10}
