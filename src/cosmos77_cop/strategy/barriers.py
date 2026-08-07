"""Barrier-placement search: the cop's constructed win condition (playbook §4.3).

The solver is exact per barrier configuration, but placement itself cannot live inside it — an
action space including "place any legal barrier" is infeasible. This is the heuristic layer above
it, with the one invariant that matters: never cut ourselves out of the thief's component.
"""

from __future__ import annotations

from ..engine.board import Board, Coord
from ..engine.rules import legal_barrier_cells
from . import solver
from .pathing import reachable_region


def plies_to_thief_moves(plies: int) -> int:
    """Solver plies converted to the thief moves they consume."""
    return (plies + 1) // 2


def wall_affinity(board: Board, cell: Coord) -> int:
    """How much a cell continues an existing wall or edge (higher builds better walls)."""
    row, col = cell
    edge = row in (0, board.size - 1) or col in (0, board.size - 1)
    near_barrier = any(n in board.barriers for n in board.neighbors4(cell))
    return int(edge) + int(near_barrier)


def best_placement(board: Board, cop: Coord, thief: Coord, min_cut: int) -> Coord | None:
    """The best region-cutting placement, or None when no candidate cuts >= *min_cut* cells."""
    current = len(reachable_region(board, thief))
    best: tuple[tuple[int, int, int], Coord] | None = None
    for cell in legal_barrier_cells(board, cop):
        if cell == thief:
            continue
        trial = board.copy()
        trial.add_barrier(cell)
        region_cells = reachable_region(trial, thief)
        # Never wall ourselves OUT of the thief's region: a cut that separates the two
        # components hands the thief a guaranteed survival, however much area it removes.
        if cop not in region_cells:
            continue
        region = len(region_cells)
        if current - region < min_cut:
            continue
        d = abs(cell[0] - thief[0]) + abs(cell[1] - thief[1])
        key = (region, -wall_affinity(board, cell), d)
        if best is None or key < best[0]:
            best = (key, cell)
    return best[1] if best else None


def finite_placement(
    board: Board, cop: Coord, thief: Coord, thief_moves_left: int
) -> Coord | None:
    """A placement that turns the solver value FINITE within budget — the constructed win."""
    best: tuple[int, Coord] | None = None
    for cell in legal_barrier_cells(board, cop):
        if cell == thief:
            continue
        trial = board.copy()
        trial.add_barrier(cell)
        value = solver.steps_to_capture(trial, cop, thief, thief_to_move=True)
        in_budget = value is not None and plies_to_thief_moves(value) + 1 <= thief_moves_left
        if in_budget and (best is None or value < best[0]):
            best = (value, cell)
    return best[1] if best else None


def herd_cell(board: Board, thief: Coord) -> Coord:
    """The cell one step from the thief toward the board center.

    Standing there pushes a distance-maximizing evader toward the walls and corners, which is
    where barrier surgery converts.
    """
    center = (board.size // 2, board.size // 2)
    gaps = (center[0] - thief[0], center[1] - thief[1])
    if gaps == (0, 0):
        return thief
    axes = sorted((0, 1), key=lambda a: -abs(gaps[a]))
    for axis in axes:
        if gaps[axis] == 0:
            continue
        step = (1 if gaps[axis] > 0 else -1, 0) if axis == 0 else (0, 1 if gaps[axis] > 0 else -1)
        cell = (thief[0] + step[0], thief[1] + step[1])
        if board.is_open(cell):
            return cell
    return thief


