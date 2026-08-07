"""Opponent-position tracker: exact scent-grid inversion with a degraded fallback (§4.1).

Under ``subtractive_chebyshev_v1`` the opponent transmits its scent grid every turn and the fresh
center deposit (0.9, decay only 0.1/step) dominates every stale cell — so the argmax of the
received grid IS the emitter's current cell (kit-measured 224/224). An empty grid (the
``multiplicative_book_v1`` convention) degrades the tracker to ``fuzzy``, and the belief map
takes over.
"""

from __future__ import annotations

from ..engine.board import Coord

EXACT = "exact"
FUZZY = "fuzzy"


def parse_grid(grid: dict[str, float]) -> dict[Coord, float]:
    """Parse wire keys ``"r,c"`` into coordinates, ignoring malformed entries."""
    cells: dict[Coord, float] = {}
    for key, value in grid.items():
        parts = key.split(",")
        if len(parts) == 2 and parts[0].lstrip("-").isdigit() and parts[1].lstrip("-").isdigit():
            cells[(int(parts[0]), int(parts[1]))] = float(value)
    return cells


class Tracker:
    """Consumes the opponent's transmitted smell grids and estimates its current cell."""

    def __init__(self) -> None:
        """Start with no observations (confidence ``fuzzy`` until a grid arrives)."""
        self.previous: dict[Coord, float] = {}
        self.cell: Coord | None = None
        self.confidence = FUZZY

    def observe_grid(self, grid: dict[str, float]) -> None:
        """Ingest one received ``smell_grid``; empty means not-transmitted (stay fuzzy)."""
        cells = parse_grid(grid)
        if not cells:
            self.confidence = FUZZY
            return
        best = max(
            cells.items(),
            key=lambda item: (item[1], item[1] - self.previous.get(item[0], 0.0), item[0]),
        )
        self.cell = best[0]
        self.confidence = EXACT
        self.previous = cells

    def estimate(self) -> tuple[Coord | None, str]:
        """The best current estimate: ``(cell, "exact")`` or ``(last known or None, "fuzzy")``."""
        return self.cell, self.confidence
