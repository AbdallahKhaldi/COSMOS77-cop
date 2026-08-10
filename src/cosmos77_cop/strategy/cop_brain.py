"""Cop decision layer: exact pursuit, two-regime barrier planning, truthful claims (§4.3).

Pure function of (board knowledge, tracker estimate, quota, budget, params) — no I/O, no LLM.
Building regime (solver value infinite): barriers shrink the thief's reachable region toward a
corner. Finishing regime (finite value): pursue the solver line within the step budget, keeping
``reserve_barriers`` for the rule-46 finisher.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.board import Board, Coord
from ..engine.rules import destination, legal_move_tokens, token_between
from . import jitter, solver
from .barriers import best_placement, finite_placement, herd_cell
from .params import StrategyParams
from .pathing import bfs_distances


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
    if barriers_left >= 1:
        winning = finite_placement(board, cop, thief, thief_moves_left)
        if winning is not None:
            return CopAction("barrier", barrier_cell=winning)
    near = abs(cop[0] - thief[0]) + abs(cop[1] - thief[1]) <= params.place_range
    if barriers_left > params.reserve_barriers and near:
        placement = best_placement(board, cop, thief)
        if placement is not None:
            return CopAction("barrier", barrier_cell=placement)
    target = herd_cell(board, thief)
    chase = target if target != cop else thief
    return _move(cop, _token_toward(board, cop, chase), thief)


def decide_fuzzy(
    board: Board,
    cop: Coord,
    posterior: dict[Coord, float],
    params: StrategyParams,
) -> CopAction:
    """The cop's turn under a belief map: minimize expected distance; probe only when sure."""
    costed = []
    for token in legal_move_tokens(board, cop):
        dest = destination(cop, token)
        dist = bfs_distances(board, dest)
        cost = sum(p * dist.get(cell, 10**6) for cell, p in posterior.items())
        costed.append((cost, token))
    _, best_token = jitter.pick_min(costed, key=lambda ct: ct[0], legacy=lambda ct: ct)
    target, top_p = max(posterior.items(), key=lambda kv: (kv[1], kv[0]))
    dest = destination(cop, str(best_token))
    claim = dest if dest == target and top_p >= params.claim_threshold else None
    return CopAction("move", move_token=best_token, capture_claim=claim)
