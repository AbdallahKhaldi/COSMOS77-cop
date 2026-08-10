"""Barrier-placement search: the cop's constructed win condition (playbook §4.3).

The solver is exact per barrier configuration, but placement itself cannot live inside it — an
action space including "place any legal barrier" is infeasible. This is the heuristic layer above
it, with the one invariant that matters: never cut ourselves out of the thief's component.

A curve that separates a 4-connected grid is an 8-CONNECTED chain of blocked cells: a diagonal
step buys a whole cell of separation for one barrier, an orthogonal step usually buys nothing.
Every wall-geometry measure below is therefore taken over KING moves, never ``neighbors4``.
"""

from __future__ import annotations

from collections import deque

from ..engine.board import Board, Coord
from ..engine.rules import legal_barrier_cells
from . import jitter, solver
from .pathing import reachable_region

KING: tuple[Coord, ...] = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def plies_to_thief_moves(plies: int) -> int:
    """Solver plies converted to the thief moves they consume."""
    return (plies + 1) // 2


def _on_rim(board: Board, cell: Coord) -> bool:
    return cell[0] in (0, board.size - 1) or cell[1] in (0, board.size - 1)


def touching(board: Board, cell: Coord) -> int:
    """Existing barriers 8-adjacent to *cell* — the connectivity that actually separates."""
    return sum(1 for d in KING if (cell[0] + d[0], cell[1] + d[1]) in board.barriers)


def anchor_gap(board: Board, cell: Coord) -> int:
    """Further placements needed to anchor this wall end to the board rim (0-1 BFS, king moves).

    Existing barriers are free (cost 0) and open cells cost one placement each, so the answer is
    literally "how many more barriers until this end of the wall closes". A wall end already on
    the rim is anchored and scores 0.
    """
    if _on_rim(board, cell):
        return 0
    queue, seen, best = deque([(cell, 0)]), {cell}, board.size
    while queue:
        cur, cost = queue.popleft()
        if cost >= best:
            continue
        for delta in KING:
            nxt = (cur[0] + delta[0], cur[1] + delta[1])
            if not board.in_bounds(nxt) or nxt in seen:
                continue
            step = 0 if nxt in board.barriers else 1
            seen.add(nxt)
            if _on_rim(board, nxt):
                best = min(best, cost + step)
            (queue.appendleft if step == 0 else queue.append)((nxt, cost + step))
    return best


def hug(board: Board, region_cells: set[Coord]) -> int:
    """(surviving-region cell, king-adjacent barrier) incidences — how tightly the net fits."""
    walls = board.barriers
    return sum(1 for c in region_cells for d in KING if (c[0] + d[0], c[1] + d[1]) in walls)


def best_placement(board: Board, cop: Coord, thief: Coord) -> Coord | None:
    """The best wall-building placement: smallest surviving region, then wall COMPLETION.

    Any cut >= 1 is admissible — one barrier on the bare 2-connected grid removes exactly its own
    cell, so a larger admission gate could never admit a FIRST wall (playbook §4.3: never gate
    building on an unreachable first step). What RANKS the admitted candidates is how much closer
    each brings the wall to closing: placements still needed to anchor this end to the rim, then
    8-adjacency to the existing front, then closeness to the thief, then how tightly the surviving
    region already hugs the barrier set. The cell itself terminates the key so the pick is total.
    The seal-out guard is unconditional.
    """
    current = len(reachable_region(board, thief))
    scored: list[tuple[tuple[int, ...], Coord]] = []
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
        if current - region < 1:
            continue
        d = abs(cell[0] - thief[0]) + abs(cell[1] - thief[1])
        key = (
            region,
            anchor_gap(trial, cell),
            -touching(board, cell),
            d,
            -hug(trial, region_cells),
            *cell,
        )
        scored.append((key, cell))
    if not scored:
        return None
    _, cell = jitter.pick_min(scored, key=lambda kv: kv[0], legacy=lambda kv: (kv[0], kv[1]))
    return cell


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
