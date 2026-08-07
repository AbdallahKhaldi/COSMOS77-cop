"""Full-information sub-game referee: turn order, endings, quota, scoring (rules 46-48).

Used by tests, the solver, audit physics replay, and selfplay. Live play never feeds it the
opponent's hidden position — each peer runs it only where full information legitimately exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from .board import Board, Coord
from .capture import is_co_location, is_rule46, is_rule47_boxed
from .config import GameConfig
from .rules import IllegalMoveError, apply_move, validate_barrier_placement

POLICE = "police"
THIEF = "thief"

ZEROED_RESULTS = ("timeout", "technical_loss", "tamper_forfeit")


class TurnError(RuntimeError):
    """An action out of turn or after the sub-game ended (state-machine rule 5)."""


@dataclass(frozen=True)
class Outcome:
    """How a sub-game ended; zeroed results carry no winner (a sanction, not a tie)."""

    result: str
    winner_role: str | None
    steps: int
    capture_family: str | None = None


def score_for(outcome: Outcome, cfg: GameConfig) -> dict[str, int]:
    """Per-role points for *outcome* from the fixed table (rule 48); totals derive from this."""
    table = cfg.scoring
    if outcome.result == "capture":
        return {POLICE: table["capture_cop"], THIEF: table["capture_thief"]}
    if outcome.result == "survival":
        return {POLICE: table["survival_cop"], THIEF: table["survival_thief"]}
    zero = table["technical_loss"]
    return {POLICE: zero, THIEF: zero}


class SubGame:
    """One sub-game: thief moves first; a barrier placement replaces the cop's move."""

    def __init__(self, cfg: GameConfig) -> None:
        """Set up the board and both agents from the validated constitution."""
        self.cfg = cfg
        self.board = Board(cfg.grid_size)
        self.pos: dict[str, Coord] = {POLICE: cfg.cop_start, THIEF: cfg.thief_start}
        self.mover = THIEF
        self.moves_made: dict[str, int] = {POLICE: 0, THIEF: 0}
        self.barriers_left = cfg.max_barriers
        self.outcome: Outcome | None = None

    @property
    def over(self) -> bool:
        """True once an outcome exists; every further action raises :class:`TurnError`."""
        return self.outcome is not None

    def _require_turn(self, role: str) -> None:
        if self.over:
            raise TurnError("sub-game already ended")
        if self.mover != role:
            raise TurnError(f"it is the {self.mover}'s turn, not the {role}'s")

    def _finish(self, result: str, winner: str | None, family: str | None = None) -> Outcome:
        self.outcome = Outcome(result, winner, self.moves_made[THIEF], family)
        return self.outcome

    def move(self, role: str, token: str) -> Coord:
        """Apply *role*'s move *token*; detect co-location capture and survival."""
        self._require_turn(role)
        self.pos[role] = apply_move(self.board, self.pos[role], token)
        self.moves_made[role] += 1
        if is_co_location(self.pos[POLICE], self.pos[THIEF]):
            self._finish("capture", POLICE, "co_location")
        elif role == THIEF and self.moves_made[THIEF] >= self.cfg.survival_threshold:
            self._finish("survival", THIEF)
        self._pass_turn()
        return self.pos[role]

    def place_barrier(self, cell: Coord) -> None:
        """Cop-only: barrier *cell* instead of moving; detect rule-46/47 captures."""
        self._require_turn(POLICE)
        if self.barriers_left <= 0:
            raise IllegalMoveError("barrier quota exhausted")
        validate_barrier_placement(self.board, self.pos[POLICE], cell)
        self.board.add_barrier(cell)
        self.barriers_left -= 1
        self.moves_made[POLICE] += 1
        if is_rule46(cell, self.pos[THIEF]):
            self._finish("capture", POLICE, "rule_46")
        elif is_rule47_boxed(self.board, self.pos[THIEF]):
            self._finish("capture", POLICE, "rule_47")
        self._pass_turn()

    def settle(self, result: str) -> Outcome:
        """End the sub-game from outside play (timeout / technical_loss / tamper_forfeit)."""
        if result not in ZEROED_RESULTS:
            raise ValueError(f"settle() only accepts zeroed results, got {result!r}")
        if self.over:
            raise TurnError("sub-game already ended")
        return self._finish(result, None)

    def _pass_turn(self) -> None:
        if not self.over:
            self.mover = THIEF if self.mover == POLICE else POLICE
