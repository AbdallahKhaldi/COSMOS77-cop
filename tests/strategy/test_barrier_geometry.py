"""Wall geometry behind the A1 ranking key: 8-connectivity, rim anchoring, enclosure tightness.

A curve that separates a 4-connected grid is an 8-connected chain of blocked cells anchored to
two rim points; these three primitives are what make the key measure wall COMPLETION rather than
raw proximity, so each is pinned directly rather than only through the duel sweep.
"""

from cosmos77_cop.engine.board import Board
from cosmos77_cop.strategy.barriers import anchor_gap, best_placement, hug, touching


def test_touching_counts_diagonals_and_ignores_the_candidate_cell():
    b = Board(7)
    assert touching(b, (3, 3)) == 0
    b.add_barrier((2, 2))  # diagonal — the step that actually extends a separator
    b.add_barrier((3, 4))  # orthogonal
    assert touching(b, (3, 3)) == 2
    b.add_barrier((3, 3))
    assert touching(b, (3, 3)) == 2, "the candidate cell must not count itself"


def test_anchor_gap_is_zero_on_the_rim_and_counts_open_king_steps_inland():
    b = Board(7)
    for rim in [(0, 3), (6, 3), (3, 0), (3, 6), (0, 0)]:
        assert anchor_gap(b, rim) == 0
    assert anchor_gap(b, (3, 3)) == 3, "bare board: three more placements reach the nearest rim"
    assert anchor_gap(b, (2, 3)) == 2
    assert anchor_gap(b, (1, 3)) == 1


def test_anchor_gap_walks_existing_barriers_for_free():
    b = Board(7)
    for cell in [(2, 2), (1, 1)]:
        b.add_barrier(cell)
    assert anchor_gap(b, (3, 3)) == 1, "an existing diagonal chain costs nothing to reuse"


def test_hug_counts_region_to_barrier_king_incidences():
    b = Board(7)
    assert hug(b, {(0, 0), (0, 1)}) == 0
    b.add_barrier((1, 1))
    assert hug(b, {(0, 0), (0, 1)}) == 2
    assert hug(b, {(4, 4)}) == 0


def test_best_placement_never_returns_a_cell_that_seals_the_cop_out():
    """The unconditional guard: the only candidate that cuts is the one that separates us."""
    b = Board(7)
    for col in range(3, 7):
        b.add_barrier((1, col))
    cop, thief = (0, 2), (0, 4)
    assert best_placement(b, cop, thief) != (0, 3)


def test_best_placement_returns_none_when_no_candidate_cuts_anything():
    """A cop with no legal placement at all (own cell is the thief's, no open neighbours)."""
    b = Board(7)
    for cell in [(0, 1), (1, 0)]:
        b.add_barrier(cell)
    assert best_placement(b, (0, 0), (0, 0)) is None
