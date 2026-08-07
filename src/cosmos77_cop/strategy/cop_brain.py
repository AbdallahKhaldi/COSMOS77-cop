"""Cop decision layer: exact pursuit, two-regime barrier planning, truthful claims (§4.3).

Pure function of (board knowledge, tracker estimate, quota, budget, params) — no I/O, no LLM.
Building regime (solver value infinite): barriers shrink the thief's reachable region toward a
corner. Finishing regime (finite value): pursue the solver line within the step budget, keeping
``reserve_barriers`` for the rule-46 finisher.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.board import Board, Coord
from ..engine.rules import destination, legal_barrier_cells, legal_move_tokens, token_between
from . import solver
from .params import StrategyParams
from .pathing import bfs_distances, reachable_region


@dataclass(frozen=True)
class CopAction:
    """One cop turn: a move (optionally claiming capture at the landing) or a barrier."""

    kind: str
    move_token: str | None = None
    barrier_cell: Coord | None = None
    capture_claim: Coord | None = None


def _move(cop: Coord, token: str, thief: Coord | None) -> CopAction:
    claim = destination(cop, token) if thief == destination(cop, token) else None
    return CopAction("move", move_token=token, capture_claim=claim)


def _token_toward(board: Board, cop: Coord, target: Coord) -> str:
    dist = bfs_distances(board, target)
    tokens = legal_move_tokens(board, cop)
    return min(tokens, key=lambda t: (dist.get(destination(cop, t), 10**6), t))


def _wall_affinity(board: Board, cell: Coord) -> int:
    row, col = cell
    edge = row in (0, board.size - 1) or col in (0, board.size - 1)
    near_barrier = any(n in board.barriers for n in board.neighbors4(cell))
    return int(edge) + int(near_barrier)


def _best_placement(board: Board, cop: Coord, thief: Coord) -> Coord | None:
    """The region-shrinking placement, or None when no candidate makes progress."""
    current = len(reachable_region(board, thief))
    best: tuple[tuple[int, int, int], Coord] | None = None
    for cell in legal_barrier_cells(board, cop):
        if cell == thief:
            continue
        trial = board.copy()
        trial.add_barrier(cell)
        region = len(reachable_region(trial, thief))
        if region >= current:
            continue
        d = abs(cell[0] - thief[0]) + abs(cell[1] - thief[1])
        key = (region, -_wall_affinity(board, cell), d)
        if best is None or key < best[0]:
            best = (key, cell)
    return best[1] if best else None


def _plies_to_thief_moves(plies: int) -> int:
    return (plies + 1) // 2


def decide_exact(
    board: Board,
    cop: Coord,
    thief: Coord,
    barriers_left: int,
    thief_moves_left: int,
    params: StrategyParams,
) -> CopAction:
    """The cop's turn against an exactly-tracked thief."""
    if thief in board.open_neighbors(cop):
        if barriers_left >= 1:
            return CopAction("barrier", barrier_cell=thief)
        return CopAction("move", move_token=token_between(cop, thief), capture_claim=thief)
    value = solver.steps_to_capture(board, cop, thief, thief_to_move=False)
    if value is not None and _plies_to_thief_moves(value) <= thief_moves_left:
        move = solver.best_cop_move(board, cop, thief)
        if move is not None:
            return _move(cop, token_between(cop, move[0]), thief)
    if barriers_left > params.reserve_barriers:
        placement = _best_placement(board, cop, thief)
        if placement is not None:
            return CopAction("barrier", barrier_cell=placement)
    return _move(cop, _token_toward(board, cop, thief), thief)


def decide_fuzzy(
    board: Board,
    cop: Coord,
    posterior: dict[Coord, float],
    params: StrategyParams,
) -> CopAction:
    """The cop's turn under a belief map: minimize expected distance; probe only when sure."""
    best_token = None
    best_cost = None
    for token in legal_move_tokens(board, cop):
        dest = destination(cop, token)
        dist = bfs_distances(board, dest)
        cost = sum(p * dist.get(cell, 10**6) for cell, p in posterior.items())
        if best_cost is None or (cost, token) < (best_cost, best_token):
            best_token, best_cost = token, cost
    target, top_p = max(posterior.items(), key=lambda kv: (kv[1], kv[0]))
    dest = destination(cop, str(best_token))
    claim = dest if dest == target and top_p >= params.claim_threshold else None
    return CopAction("move", move_token=best_token, capture_claim=claim)
