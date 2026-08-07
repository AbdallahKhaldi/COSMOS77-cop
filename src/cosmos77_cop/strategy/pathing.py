"""Shortest paths and reachability on the barriered grid (BFS; shared by brains and belief)."""

from __future__ import annotations

from collections import deque

from ..engine.board import Board, Coord


def bfs_distances(board: Board, src: Coord) -> dict[Coord, int]:
    """Orthogonal-step distances from *src* to every reachable open cell (src included, 0)."""
    dist = {src: 0}
    queue = deque([src])
    while queue:
        cell = queue.popleft()
        for nxt in board.open_neighbors(cell):
            if nxt not in dist:
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
    return dist


def reachable_region(board: Board, src: Coord) -> set[Coord]:
    """The set of open cells reachable from *src* (the thief's world under a barrier plan)."""
    return set(bfs_distances(board, src))
