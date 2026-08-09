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


def test_far_from_thief_herds_instead_of_wasting_barriers():
    b = Board(7)
    action = decide_exact(b, (0, 0), (1, 5), barriers_left=14, thief_moves_left=30, params=PARAMS)
    assert action.kind == "move"


def test_a_placement_that_seals_us_out_is_never_chosen():
    b = Board(7)
    for col in range(3, 7):
        b.add_barrier((1, col))
    cop, thief = (0, 2), (0, 4)
    action = decide_exact(b, cop, thief, barriers_left=14, thief_moves_left=30, params=PARAMS)
    assert action.barrier_cell != (0, 3)


def test_finite_placement_fires_even_at_reserve():
    b = Board(7)
    for cell in [(1, 4), (1, 5), (1, 6), (0, 4)]:
        b.add_barrier(cell)
    action = decide_exact(b, (0, 6), (0, 5), barriers_left=1, thief_moves_left=30, params=PARAMS)
    assert action.kind == "barrier"


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


def _greedy_evade(board: Board, thief, cop, exit_bonus=0.5):
    """The kit sparring peer's GreedyEvade, reimplemented so the regression is self-contained."""
    from cosmos77_cop.engine.rules import legal_move_tokens

    def score(cell):
        away = abs(cell[0] - cop[0]) + abs(cell[1] - cop[1])
        return away + exit_bonus * len(board.open_neighbors(cell))

    tokens = legal_move_tokens(board, thief)
    ranked = sorted(tokens, key=lambda m: (-score(destination(thief, m)), m))
    return destination(thief, ranked[0])


def _duel(thief_start, max_moves=35, quota=14):
    from cosmos77_cop.engine.capture import is_rule46, is_rule47_boxed

    board = Board(7)
    cop, thief = (0, 0), thief_start
    left = quota
    for move_no in range(1, max_moves + 1):
        thief = _greedy_evade(board, thief, cop)
        if thief == cop or is_rule47_boxed(board, thief):
            return "capture", move_no, quota - left
        action = decide_exact(
            board, cop, thief, barriers_left=left, thief_moves_left=max_moves - move_no,
            params=PARAMS,
        )
        if action.kind == "barrier":
            board.add_barrier(action.barrier_cell)
            left -= 1
            assert left >= 0, "quota exceeded"
            region = reachable_region(board, thief)
            assert cop in region, "sealed ourselves out of the thief's region"
            if is_rule46(action.barrier_cell, thief) or is_rule47_boxed(board, thief):
                return "capture", move_no, quota - left
        else:
            cop = destination(cop, action.move_token)
            if cop == thief:
                return "capture", move_no, quota - left
    return "survival", max_moves, quota - left


@pytest.mark.parametrize("thief_start", [(3, 3), (6, 6), (0, 6), (5, 2), (2, 5)])
def test_cop_converts_against_the_kit_greedy_evader(thief_start):
    """Frozen Phase-8 regression: capture within budget, quota respected, never sealed out."""
    outcome, moves, used = _duel(thief_start)
    assert outcome == "capture", f"greedy evader survived from {thief_start}"
    assert moves <= 25
    assert used <= 14


def _solver_evade(board: Board, thief, cop):
    """A distance-keeping solver thief (the audit's probe): survives any wall-less cop."""
    from cosmos77_cop.strategy.solver import best_thief_move

    dest, _ = best_thief_move(board, cop, thief)
    return dest if dest is not None else thief


def test_building_regime_fires_from_a_bare_board():
    """Playbook §4.3: the first wall must never be gated on an unreachable cut threshold."""
    action = decide_exact(
        Board(7), (3, 4), (3, 2), barriers_left=14, thief_moves_left=30, params=PARAMS
    )
    assert action.kind == "barrier", "cop must start building against a distance-keeper"


def _solver_duel(thief_start, max_moves=35, quota=14):
    board = Board(7)
    cop, thief = (0, 0), thief_start
    left = quota
    placed = 0
    for move_no in range(1, max_moves + 1):
        thief = _solver_evade(board, thief, cop)
        if thief == cop or is_rule47_boxed_(board, thief):
            return "capture", move_no, placed
        action = decide_exact(
            board, cop, thief, barriers_left=left, thief_moves_left=max_moves - move_no,
            params=PARAMS,
        )
        if action.kind == "barrier":
            board.add_barrier(action.barrier_cell)
            left -= 1
            placed += 1
            assert left >= 0, "quota exceeded"
            region = reachable_region(board, thief)
            assert cop in region, "sealed ourselves out of the thief's region"
            from cosmos77_cop.engine.capture import is_rule46

            if is_rule46(action.barrier_cell, thief) or is_rule47_boxed_(board, thief):
                return "capture", move_no, placed
        else:
            cop = destination(cop, action.move_token)
            if cop == thief:
                return "capture", move_no, placed
    return "survival", max_moves, placed


def is_rule47_boxed_(board, thief):
    from cosmos77_cop.engine.capture import is_rule47_boxed

    return is_rule47_boxed(board, thief)


@pytest.mark.parametrize(
    ("thief_start", "converts"), [((3, 3), False), ((6, 6), True), ((2, 5), True)]
)
def test_cop_genuinely_builds_walls_against_a_distance_keeping_thief(thief_start, converts):
    """Re-frozen Phase-8 regression: vs the solver evader the cop must actually place walls
    (it previously placed 0/35 and lost every such duel — the audit's dead-regime finding)."""
    outcome, _moves, placed = _solver_duel(thief_start)
    assert placed >= 3, f"cop placed only {placed} barriers vs solver thief from {thief_start}"
    if converts:
        assert outcome == "capture", f"cop no longer converts the solver thief from {thief_start}"
