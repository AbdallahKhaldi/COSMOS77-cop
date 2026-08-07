"""Board geometry: bounds, neighbors, permanent barriers."""

import pytest

from cosmos77_cop.engine.board import BarrierError, Board


def test_bounds_and_openness():
    b = Board(7)
    assert b.in_bounds((0, 0)) and b.in_bounds((6, 6))
    assert not b.in_bounds((-1, 0)) and not b.in_bounds((0, 7))
    b.add_barrier((3, 3))
    assert not b.is_open((3, 3)) and b.is_open((3, 4)) and not b.is_open((7, 7))


@pytest.mark.parametrize(
    ("cell", "count"),
    [((0, 0), 2), ((0, 3), 3), ((3, 3), 4), ((6, 6), 2), ((6, 3), 3)],
)
def test_neighbors4_by_position(cell, count):
    assert len(Board(7).neighbors4(cell)) == count


def test_open_neighbors_shrink_with_barriers():
    b = Board(7)
    b.add_barrier((2, 3))
    b.add_barrier((3, 2))
    assert sorted(b.open_neighbors((3, 3))) == [(3, 4), (4, 3)]


def test_barrier_rejections_and_permanence():
    b = Board(7)
    b.add_barrier((1, 1))
    with pytest.raises(BarrierError, match="already"):
        b.add_barrier((1, 1))
    with pytest.raises(BarrierError, match="off-board"):
        b.add_barrier((7, 0))
    assert (1, 1) in b.barriers


def test_copy_is_independent():
    b = Board(7, {(1, 1)})
    c = b.copy()
    c.add_barrier((2, 2))
    assert (2, 2) not in b.barriers and (1, 1) in c.barriers
