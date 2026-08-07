"""Bridge from live tracked knowledge to THIS repo's brain (the cop; pure Python, rule 25)."""

from __future__ import annotations

from ..belief.bayes import BeliefMap
from ..engine.board import Coord
from ..hints.liar_score import direction_matches, hinted_direction
from ..strategy.cop_brain import CopAction, decide_exact, decide_fuzzy
from ..strategy.params import StrategyParams
from ..strategy.tracker import EXACT
from .turnstate import SideKit, TurnState

ROLE = "police"


class BrainBridge:
    """Per-sub-game decision wiring: tracker first, belief fallback, truthful claims only."""

    def __init__(self, state: TurnState, params: StrategyParams | None = None) -> None:
        """Seed the belief map at the opponent's constitution start cell."""
        self.params = params or StrategyParams()
        self.belief = BeliefMap(state.board, state.cfg.thief_start)
        self.my_last_claim: Coord | None = None

    def note_opponent_turn(self, state: TurnState, kit: SideKit, hint: str) -> None:
        """Advance the belief one opponent move and fold in liar-weighted hint evidence.

        The factor maps the liar-score onto [0.5, 1.5]: a caught liar's claimed region is
        DISFAVORED, an honest opponent's favored, an uncalibrated one ignored.
        """
        self.belief.diffuse()
        direction = hinted_direction(hint) if hint else None
        if direction is not None:
            grid = state.cfg.grid_size
            cells = {c for c in self.belief.posterior() if direction_matches(direction, c, grid)}
            if cells:
                self.belief.condition_region(cells, 0.5 + kit.liar.weight())

    def note_claim_answered_false(self, cell: Coord) -> None:
        """A probe we sent came back ``caught: false`` — hard evidence."""
        self.belief.condition_not_at(cell)

    def decide(self, state: TurnState, kit: SideKit) -> CopAction:
        """One cop turn from current knowledge."""
        cell, confidence = kit.tracker.estimate()
        thief_moves_left = max(0, state.cfg.survival_threshold - state.their_turns)
        if confidence == EXACT and cell is not None and state.board.is_open(cell):
            action = decide_exact(
                state.board,
                state.my_pos,
                cell,
                barriers_left=state.barriers_left,
                thief_moves_left=thief_moves_left,
                params=self.params,
            )
        else:
            action = decide_fuzzy(state.board, state.my_pos, self.belief.posterior(), self.params)
        if action.capture_claim is not None:
            self.my_last_claim = action.capture_claim
        return action
