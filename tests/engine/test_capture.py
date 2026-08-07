"""The three capture families, incl. the rule-47 brute-force cross-check property."""

import random

from cosmos77_cop.engine.board import Board
from cosmos77_cop.engine.capture import (
    concession_payload,
    is_co_location,
    is_rule46,
    is_rule47_boxed,
)


def test_co_location_and_rule46_are_exact_cell_matches():
    assert is_co_location((2, 2), (2, 2)) and not is_co_location((2, 2), (2, 3))
    assert is_rule46((5, 5), (5, 5)) and not is_rule46((5, 4), (5, 5))


def test_rule47_corner_needs_two_barriers():
    b = Board(7)
    b.add_barrier((0, 1))
    assert not is_rule47_boxed(b, (0, 0))
    b.add_barrier((1, 0))
    assert is_rule47_boxed(b, (0, 0))


def test_rule47_center_needs_all_four():
    b = Board(7)
    for cell in [(2, 3), (4, 3), (3, 2)]:
        b.add_barrier(cell)
    assert not is_rule47_boxed(b, (3, 3))
    b.add_barrier((3, 4))
    assert is_rule47_boxed(b, (3, 3))


def _boxed_ground_truth(b: Board, thief) -> bool:
    row, col = thief
    around = [(row - 1, col), (row + 1, col), (row, col + 1), (row, col - 1)]
    return all(not b.is_open(c) for c in around)


def test_rule47_matches_brute_force_everywhere():
    rng = random.Random(4747)
    cells = [(r, c) for r in range(7) for c in range(7)]
    for _ in range(300):
        b = Board(7, {cells[i] for i in rng.sample(range(49), rng.randint(0, 14))})
        for thief in cells:
            if thief in b.barriers:
                continue
            assert is_rule47_boxed(b, thief) == _boxed_ground_truth(b, thief)


def test_concession_payload_names_own_cell():
    assert concession_payload((4, 1)) == {"claim": [4, 1], "caught": True}
