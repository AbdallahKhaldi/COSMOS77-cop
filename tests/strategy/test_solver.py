"""Solver ground truth: empty-board thief-win, trap conversion, rule-46 radius, speed, memo."""

import random
import time

import pytest

from cosmos77_cop.engine.board import Board
from cosmos77_cop.engine.rules import apply_move, destination, legal_move_tokens, token_between
from cosmos77_cop.strategy import solver


@pytest.fixture(autouse=True)
def _fresh_cache():
    solver.clear_cache()
    yield
    solver.clear_cache()


def test_empty_board_is_thief_win_from_standard_start():
    b = Board(7)
    assert solver.steps_to_capture(b, (0, 0), (3, 3), thief_to_move=True) is None


def test_empty_board_thief_win_from_every_distant_start():
    b = Board(7)
    tab = solver.solve(b)
    for cop in [(0, 0), (3, 3), (6, 6)]:
        for thief in [(0, 6), (6, 0), (5, 1)]:
            if thief == cop or thief in b.open_neighbors(cop):
                continue
            assert (cop, thief, solver.THIEF_TURN) not in tab.rank


def test_rule46_radius_is_a_one_ply_capture():
    b = Board(7)
    assert solver.steps_to_capture(b, (3, 3), (3, 4), thief_to_move=False) == 1
    assert solver.steps_to_capture(b, (3, 3), (2, 3), thief_to_move=False) == 1


def test_adjacent_thief_to_move_can_still_escape_on_empty_board():
    b = Board(7)
    assert solver.steps_to_capture(b, (3, 3), (3, 4), thief_to_move=True) is None


def corridor_trap() -> Board:
    """Row 0 sealed from below: a cycle-free region, hence provably cop-win once entered."""
    b = Board(7)
    for col in range(7):
        b.add_barrier((1, col))
    return b


def test_corridor_trap_is_finite_and_converts():
    b = corridor_trap()
    cop, thief = (0, 6), (0, 2)
    value = solver.steps_to_capture(b, cop, thief, thief_to_move=False)
    assert value is not None
    for _ in range(value + 1):
        move = solver.best_cop_move(b, cop, thief)
        assert move is not None
        cop = move[0]
        if cop == thief:
            break
        thief = solver.best_thief_move(b, cop, thief)[0]
    assert cop == thief


def test_a_2x2_room_still_evades_even_with_the_enlarged_capture_set():
    b = Board(7)
    for cell in [(2, 0), (2, 1), (0, 2), (1, 2)]:
        b.add_barrier(cell)
    assert solver.steps_to_capture(b, (0, 0), (1, 1), thief_to_move=True) is None


def test_boxed_thief_cells_are_terminal():
    b = Board(7)
    for cell in [(0, 1), (1, 0)]:
        b.add_barrier(cell)
    assert solver.steps_to_capture(b, (5, 5), (0, 0), thief_to_move=True) == 0
    assert solver.steps_to_capture(b, (5, 5), (0, 0), thief_to_move=False) == 0


def test_solve_speed_under_100ms():
    solver.clear_cache()
    start = time.perf_counter()
    solver.solve(Board(7))
    assert time.perf_counter() - start < 0.1


def test_memoized_by_barrier_configuration():
    b = Board(7)
    first = solver.solve(b)
    assert solver.solve(Board(7)) is first
    b2 = Board(7, {(3, 3)})
    assert solver.solve(b2) is not first
    assert solver.solve(Board(7, {(3, 3)})) is solver.solve(b2)


def _greedy(board: Board, cop, thief) -> str:
    def dist(c):
        return abs(c[0] - thief[0]) + abs(c[1] - thief[1])

    return min(legal_move_tokens(board, cop), key=lambda t: (dist(destination(cop, t)), t))


def _random_cop(rng: random.Random):
    def play(board: Board, cop, thief) -> str:
        return rng.choice(legal_move_tokens(board, cop))

    return play


def _solver_cop(board: Board, cop, thief) -> str:
    move = solver.best_cop_move(board, cop, thief)
    return token_between(cop, move[0]) if move else _greedy(board, cop, thief)


@pytest.mark.parametrize(
    ("name", "cop_policy"),
    [("greedy", _greedy), ("random", _random_cop(random.Random(7))), ("solver", _solver_cop)],
)
def test_solver_evasion_survives_35_steps_vs_any_cop(name, cop_policy):
    b = Board(7)
    cop, thief = (0, 0), (3, 3)
    for step in range(35):
        thief = solver.best_thief_move(b, cop, thief)[0]
        assert thief != cop, f"{name}: thief walked into the cop at step {step}"
        assert thief not in b.open_neighbors(cop), f"{name}: adjacent (rule-46 radius) at {step}"
        cop = apply_move(b, cop, cop_policy(b, cop, thief))
        assert cop != thief, f"{name}: captured by co-location at step {step}"
