"""Exact retrograde pursuit solver, one solve per barrier configuration (playbook §4.2).

Backward induction over every ``(cop, thief, side-to-move)`` state (at most 49*49*2 on 7x7) with
the ENLARGED capture set: with the cop to move, a thief on an adjacent open cell is already
captured (step onto it and claim, or drop the rule-46 barrier). Boxed thief cells are rule-47
terminals. On the bare orthogonal board the cop number is >= 2 (C4 retract), so the empty-board
value is correctly infinite — returned as ``None``. Ported from HW6 ``strategy/pursuit.py``
(king-move, cop-win) and re-derived for the thief-win orthogonal board with barriers.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from ..engine.board import Board, Coord
from . import jitter

COP_TURN = 0
THIEF_TURN = 1

State = tuple[Coord, Coord, int]

_cache: dict[tuple[int, frozenset[Coord]], Tables] = {}


@dataclass(frozen=True)
class Tables:
    """Solved position table for one barrier configuration."""

    rank: dict[State, int]
    land: dict[Coord, list[Coord]]


def clear_cache() -> None:
    """Drop all memoized solves (test isolation)."""
    _cache.clear()


def solve(board: Board) -> Tables:
    """Solve (or return the memoized solve for) *board*'s exact barrier configuration."""
    key = (board.size, frozenset(board.barriers))
    if key not in _cache:
        _cache[key] = _solve(board)
    return _cache[key]


def _solve(board: Board) -> Tables:
    size = board.size
    open_cells = [(r, c) for r in range(size) for c in range(size) if board.is_open((r, c))]
    land = {c: [c, *board.open_neighbors(c)] for c in open_cells}
    boxed = {c for c in open_cells if len(land[c]) == 1}
    rank: dict[State, int] = {}
    heap: list[tuple[int, State]] = []

    def seed(state: State, r: int) -> None:
        if state not in rank:
            rank[state] = r
            heapq.heappush(heap, (r, state))

    for t in boxed:
        for c in open_cells:
            if c != t:
                seed((c, t, COP_TURN), 0)
                seed((c, t, THIEF_TURN), 0)
    for c in open_cells:
        for t in board.open_neighbors(c):
            if t not in boxed:
                seed((c, t, COP_TURN), 1)

    cnt: dict[tuple[Coord, Coord], int] = {}
    for c in open_cells:
        for t in open_cells:
            if t != c and t not in boxed:
                cnt[(c, t)] = len([t2 for t2 in land[t] if t2 != c])

    while heap:
        r, (c, t, side) = heapq.heappop(heap)
        if rank.get((c, t, side)) != r:
            continue
        if side == COP_TURN:
            for tp in land[t]:
                if tp == c or tp in boxed or (c, tp, THIEF_TURN) in rank:
                    continue
                cnt[(c, tp)] -= 1
                if cnt[(c, tp)] == 0:
                    worst = max(rank[(c, t2, COP_TURN)] for t2 in land[tp] if t2 != c)
                    seed((c, tp, THIEF_TURN), 1 + worst)
        else:
            for cp in land[c]:
                if cp != t:
                    seed((cp, t, COP_TURN), 1 + r)
    return Tables(rank=rank, land=land)


def steps_to_capture(
    board: Board, cop: Coord, thief: Coord, *, thief_to_move: bool = True
) -> int | None:
    """Plies to capture under optimal play, or ``None`` when the thief's evasion holds (∞)."""
    if cop == thief:
        return 0
    side = THIEF_TURN if thief_to_move else COP_TURN
    return solve(board).rank.get((cop, thief, side))


def best_cop_move(board: Board, cop: Coord, thief: Coord) -> tuple[Coord, int] | None:
    """The cop's optimal landing cell and its cost, or ``None`` when no move forces capture.

    A returned landing equal to *thief* means capture-now (step on and claim); an adjacent
    thief can equally be finished with the rule-46 barrier — the brain chooses which.
    """
    tab = solve(board)
    costed: list[tuple[int, Coord]] = []
    for dest in tab.land[cop]:
        if dest == thief:
            costed.append((1, dest))
            continue
        r = tab.rank.get((dest, thief, THIEF_TURN))
        if r is not None:
            costed.append((1 + r, dest))
    if not costed:
        return None
    cost, dest = jitter.pick_min(costed, key=lambda cd: cd[0], legacy=lambda cd: cd)
    return (dest, cost)


def best_thief_move(board: Board, cop: Coord, thief: Coord) -> tuple[Coord, int | None]:
    """The thief's max-survival landing and its value (``None`` = holds evasion forever).

    Maximizes distance-to-capture, tie-breaking toward higher escape degree; never enters
    the cop's cell.
    """
    tab = solve(board)
    scored: list[tuple[tuple[float, int, int, int], Coord]] = []
    for dest in tab.land[thief]:
        if dest == cop:
            continue
        r = tab.rank.get((cop, dest, COP_TURN))
        value = float("inf") if r is None else float(r)
        scored.append(((value, len(board.open_neighbors(dest)), -dest[0], -dest[1]), dest))
    assert scored  # STAY is always available
    _, dest = jitter.pick_max(scored, key=lambda kv: kv[0][:2], legacy=lambda kv: kv[0])
    r = tab.rank.get((cop, dest, COP_TURN))
    return (dest, r)
