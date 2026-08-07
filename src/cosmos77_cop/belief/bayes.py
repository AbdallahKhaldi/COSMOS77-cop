"""Physics-constrained Bayesian belief over the opponent's cell (degraded-mode fallback).

Starts as a delta at the opponent's constitution start cell, diffuses one legal step per opponent
turn (STAY or an open orthogonal move — physics is the hard constraint), and conditions on soft
evidence: failed capture probes, hint-derived regions weighted by the opponent's liar-score.
"""

from __future__ import annotations

from ..engine.board import Board, Coord


class BeliefMap:
    """A normalized probability map over open cells."""

    def __init__(self, board: Board, start: Coord) -> None:
        """All mass on the opponent's known start cell."""
        self.board = board
        self.probs: dict[Coord, float] = {start: 1.0}

    def _normalize(self) -> None:
        total = sum(self.probs.values())
        if total <= 0.0:
            size = self.board.size
            grid = [(r, co) for r in range(size) for co in range(size)]
            cells = [c for c in grid if self.board.is_open(c)]
            self.probs = {c: 1.0 / len(cells) for c in cells}
            return
        self.probs = {c: p / total for c, p in self.probs.items() if p > 0.0}

    def diffuse(self) -> None:
        """Advance one opponent turn: mass spreads uniformly over each cell's legal landings."""
        spread: dict[Coord, float] = {}
        for cell, p in self.probs.items():
            landings = [cell, *self.board.open_neighbors(cell)]
            share = p / len(landings)
            for dest in landings:
                spread[dest] = spread.get(dest, 0.0) + share
        self.probs = spread
        self._normalize()

    def condition_not_at(self, cell: Coord) -> None:
        """Zero a cell ruled out by hard evidence (e.g. an answered-false capture probe)."""
        self.probs.pop(cell, None)
        self._normalize()

    def condition_only(self, cells: set[Coord]) -> None:
        """Hard evidence: the opponent is certainly inside *cells* (everything else is zeroed)."""
        kept = {c: p for c, p in self.probs.items() if c in cells}
        self.probs = kept or dict.fromkeys(cells, 1.0)
        self._normalize()

    def condition_region(self, cells: set[Coord], factor: float) -> None:
        """Soft evidence: multiply the region's mass by *factor* (>1 favors, <1 disfavors)."""
        self.probs = {c: p * (factor if c in cells else 1.0) for c, p in self.probs.items()}
        self._normalize()

    def argmax(self) -> tuple[Coord, float]:
        """The most likely cell and its probability (deterministic tie-break by coordinate)."""
        cell = max(self.probs, key=lambda c: (self.probs[c], -c[0], -c[1]))
        return cell, self.probs[cell]

    def posterior(self) -> dict[Coord, float]:
        """A copy of the current normalized belief."""
        return dict(self.probs)
