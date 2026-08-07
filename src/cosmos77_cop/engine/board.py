"""The grid and its permanent barriers — pure geometry, no occupancy, no I/O."""

from __future__ import annotations

Coord = tuple[int, int]

_ORTHO_DELTAS: tuple[Coord, ...] = ((-1, 0), (1, 0), (0, 1), (0, -1))


class BarrierError(ValueError):
    """An illegal barrier placement (off-board or already barriered)."""


class Board:
    """A ``size`` x ``size`` grid with a growing set of permanent barrier cells.

    Coordinates are ``(row, col)``, origin top-left, 0-indexed (App. F axis convention).
    """

    def __init__(self, size: int, barriers: set[Coord] | None = None) -> None:
        """Create a board of ``size`` x ``size`` with an optional initial barrier set."""
        self.size = size
        self.barriers: set[Coord] = set(barriers or ())

    def in_bounds(self, cell: Coord) -> bool:
        """Return True when *cell* lies on the grid."""
        row, col = cell
        return 0 <= row < self.size and 0 <= col < self.size

    def is_open(self, cell: Coord) -> bool:
        """Return True when *cell* is on the grid and not barriered."""
        return self.in_bounds(cell) and cell not in self.barriers

    def neighbors4(self, cell: Coord) -> list[Coord]:
        """The in-bounds orthogonal neighbors of *cell* (barriered or not)."""
        row, col = cell
        return [c for d in _ORTHO_DELTAS if self.in_bounds(c := (row + d[0], col + d[1]))]

    def open_neighbors(self, cell: Coord) -> list[Coord]:
        """The orthogonal neighbors of *cell* an agent could legally step onto."""
        return [c for c in self.neighbors4(cell) if c not in self.barriers]

    def add_barrier(self, cell: Coord) -> None:
        """Permanently barrier *cell*; raise :class:`BarrierError` if off-board or duplicate."""
        if not self.in_bounds(cell):
            raise BarrierError(f"barrier {cell} is off-board")
        if cell in self.barriers:
            raise BarrierError(f"barrier {cell} already placed")
        self.barriers.add(cell)

    def copy(self) -> Board:
        """An independent copy (used by the solver for hypothetical placements)."""
        return Board(self.size, set(self.barriers))
