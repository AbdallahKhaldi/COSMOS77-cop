"""Movement legality (rules 13-14) and barrier placement legality (rules 15-16)."""

import pytest

from cosmos77_cop.engine.board import Board
from cosmos77_cop.engine.rules import (
    IllegalMoveError,
    apply_move,
    destination,
    is_orthostep,
    legal_barrier_cells,
    legal_move_tokens,
    validate_barrier_placement,
)


def test_destinations_are_orthogonal_only():
    assert destination((3, 3), "N") == (2, 3)
    assert destination((3, 3), "S") == (4, 3)
    assert destination((3, 3), "E") == (3, 4)
    assert destination((3, 3), "W") == (3, 2)
    assert destination((3, 3), "STAY") == (3, 3)
    with pytest.raises(IllegalMoveError, match="unknown move token"):
        destination((3, 3), "NE")


def test_legal_tokens_center_corner_and_blocked():
    b = Board(7)
    assert set(legal_move_tokens(b, (3, 3))) == {"N", "S", "E", "W", "STAY"}
    assert set(legal_move_tokens(b, (0, 0))) == {"S", "E", "STAY"}
    b.add_barrier((2, 3))
    assert "N" not in legal_move_tokens(b, (3, 3))


def test_apply_move_validates():
    b = Board(7)
    assert apply_move(b, (0, 0), "S") == (1, 0)
    with pytest.raises(IllegalMoveError, match="off-board"):
        apply_move(b, (0, 0), "N")
    b.add_barrier((0, 1))
    with pytest.raises(IllegalMoveError, match="into a barrier"):
        apply_move(b, (0, 0), "E")
    assert apply_move(b, (0, 0), "STAY") == (0, 0)


@pytest.mark.parametrize(
    ("src", "dst", "ok"),
    [
        ((3, 3), (3, 3), True),
        ((3, 3), (2, 3), True),
        ((3, 3), (3, 4), True),
        ((3, 3), (2, 4), False),
        ((3, 3), (5, 3), False),
        ((0, 0), (6, 6), False),
    ],
)
def test_is_orthostep_shapes(src, dst, ok):
    assert is_orthostep(src, dst) is ok


def test_barrier_cells_own_cell_and_open_neighbors_only():
    b = Board(7)
    cells = legal_barrier_cells(b, (0, 0))
    assert cells == {(0, 0), (0, 1), (1, 0)}
    b.add_barrier((0, 1))
    assert legal_barrier_cells(b, (0, 0)) == {(0, 0), (1, 0)}
    validate_barrier_placement(b, (0, 0), (1, 0))
    with pytest.raises(IllegalMoveError, match="not the cop's cell"):
        validate_barrier_placement(b, (0, 0), (2, 2))
    with pytest.raises(IllegalMoveError, match="not the cop's cell"):
        validate_barrier_placement(b, (0, 0), (1, 1))
