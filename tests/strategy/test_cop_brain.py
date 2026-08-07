"""Cop brain: finisher, regimes, reserve, budget guard, fuzzy claims (PRD-3 acceptance)."""

import pytest

from cosmos77_cop.engine.board import Board
from cosmos77_cop.engine.rules import destination
from cosmos77_cop.strategy import solver
from cosmos77_cop.strategy.cop_brain import decide_exact, decide_fuzzy
from cosmos77_cop.strategy.params import StrategyParams
from cosmos77_cop.strategy.pathing import reachable_region

PARAMS = StrategyParams()


@pytest.fixture(autouse=True)
def _fresh_cache():
    solver.clear_cache()
    yield
    solver.clear_cache()


def corridor_trap() -> Board:
    b = Board(7)
    for col in range(7):
        b.add_barrier((1, col))
    return b


def test_adjacent_thief_finished_with_rule46_barrier():
    action = decide_exact(
        Board(7), (3, 3), (3, 4), barriers_left=5, thief_moves_left=30, params=PARAMS
    )
    assert action.kind == "barrier"
    assert action.barrier_cell == (3, 4)


def test_adjacent_thief_without_quota_finished_by_move_and_claim():
    action = decide_exact(
        Board(7), (3, 3), (3, 4), barriers_left=0, thief_moves_left=30, params=PARAMS
    )
    assert action.kind == "move"
    assert destination((3, 3), action.move_token) == (3, 4)
    assert action.capture_claim == (3, 4)


def test_finite_value_within_budget_pursues_the_solver_line():
    b = corridor_trap()
    cop, thief = (0, 6), (0, 2)
    before = solver.steps_to_capture(b, cop, thief, thief_to_move=False)
    action = decide_exact(b, cop, thief, barriers_left=7, thief_moves_left=30, params=PARAMS)
    assert action.kind == "move"
    dest = destination(cop, action.move_token)
    after = solver.steps_to_capture(b, dest, thief, thief_to_move=True)
    assert after is not None and before is not None and after < before


def test_building_regime_places_a_region_shrinking_barrier():
    b = Board(7)
    cop, thief = (0, 0), (3, 3)
    before = len(reachable_region(b, thief))
    action = decide_exact(b, cop, thief, barriers_left=14, thief_moves_left=30, params=PARAMS)
    assert action.kind == "barrier"
    trial = b.copy()
    trial.add_barrier(action.barrier_cell)
    assert len(reachable_region(trial, thief)) < before


def test_reserve_barriers_block_building_placements():
    action = decide_exact(
        Board(7),
        (0, 0),
        (3, 3),
        barriers_left=PARAMS.reserve_barriers,
        thief_moves_left=30,
        params=PARAMS,
    )
    assert action.kind == "move"


def test_finisher_still_fires_at_reserve():
    action = decide_exact(
        Board(7), (3, 3), (3, 4), barriers_left=1, thief_moves_left=5, params=PARAMS
    )
    assert action.kind == "barrier"
    assert action.barrier_cell == (3, 4)


def test_fuzzy_moves_toward_posterior_mass():
    posterior = {(5, 5): 1.0}
    action = decide_fuzzy(Board(7), (0, 0), posterior, PARAMS)
    assert action.kind == "move"
    dest = destination((0, 0), action.move_token)
    assert abs(dest[0] - 5) + abs(dest[1] - 5) == 9
    assert action.capture_claim is None


def test_fuzzy_claim_only_at_threshold_and_co_location():
    sure = {(1, 0): 0.95, (5, 5): 0.05}
    action = decide_fuzzy(Board(7), (0, 0), sure, PARAMS)
    assert destination((0, 0), action.move_token) == (1, 0)
    assert action.capture_claim == (1, 0)
    unsure = {(1, 0): 0.6, (5, 5): 0.4}
    action = decide_fuzzy(Board(7), (0, 0), unsure, PARAMS)
    assert action.capture_claim is None
