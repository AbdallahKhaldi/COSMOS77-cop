"""Stateful scent pipeline wiring the vendored model math into the turn loop (rule 23; §2.4).

``subtractive_chebyshev_v1``: per game-step, deposit-then-decay — emit at our cell (gated on
center >= min_center_intensity), merge into the trail by max, decay the whole trail; the decayed
trail is what crosses the wire. The receiver decays its stored copy of the opponent's grid each
step. ``multiplicative_book_v1`` transmits ``{}`` — the key is never dropped.
"""

from __future__ import annotations

from ..engine.config import GameConfig
from ..protocol.scent import merge_max, smell_decay, smell_emit

SUBTRACTIVE = "subtractive_chebyshev_v1"
MULTIPLICATIVE = "multiplicative_book_v1"

Coord = tuple[int, int]


class ScentFlow:
    """Our emitted trail and the opponent's received field, for one sub-game."""

    def __init__(self, cfg: GameConfig, model: str = SUBTRACTIVE) -> None:
        """Fresh empty fields; *model* is the pair-locked scent model name."""
        self.cfg = cfg
        self.model = model
        self.trail: dict[str, float] = {}
        self.received: dict[str, float] = {}

    def step_emit(self, self_pos: Coord) -> dict[str, float]:
        """Advance our field one game-step and return the wire form for this turn."""
        if self.model != SUBTRACTIVE:
            return {}
        if self.cfg.pheromone_center_intensity >= self.cfg.pheromone_min_center_intensity:
            fresh = smell_emit(
                self_pos,
                self.cfg.pheromone_center_intensity,
                self.cfg.pheromone_grid_size,
                self.cfg.grid_size,
            )
            self.trail = merge_max(self.trail, fresh)
        self.trail = smell_decay(self.trail, self.cfg.pheromone_decay)
        return dict(self.trail)

    def observe(self, grid: dict[str, float]) -> None:
        """Store the opponent's freshly transmitted grid (raw — the tracker reads this)."""
        if grid:
            self.received = dict(grid)

    def step_received_decay(self) -> None:
        """One game-step of receiver-side decay on our stored copy of their field."""
        if self.received:
            self.received = smell_decay(self.received, self.cfg.pheromone_decay)
