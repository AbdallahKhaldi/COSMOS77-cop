"""Per-sub-game hidden-information state: what THIS side may legally know (rules 8-9).

Own position is exact; the opponent exists only through messages (grids, hints, declarations,
claims). The full-information engine referee is never fed live opponent state — endings are
message-driven, except the thief's own rule-46/47 self-checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..engine.board import Board, Coord
from ..engine.config import GameConfig
from ..hints.gemini import HintMeter
from ..hints.liar_score import LiarScore
from ..hints.provider import HintProvider
from ..strategy.tracker import Tracker
from .scentflow import SUBTRACTIVE, ScentFlow


@dataclass
class Ending:
    """How this sub-game ended, from THIS side's evidence."""

    result: str
    winner_role: str | None
    reason: str


@dataclass
class TurnState:
    """Everything one side tracks while a sub-game runs."""

    cfg: GameConfig
    role: str
    board: Board
    my_pos: Coord
    my_moves: int = 0
    barriers_left: int = 0
    their_turns: int = 0
    pending_claim: Coord | None = None
    final_response: dict[str, Any] | None = None
    ending: Ending | None = None
    tokens_sub_game: int = 0
    tracker_trace: list[list[int] | None] = field(default_factory=list)

    @property
    def over(self) -> bool:
        """True once an ending exists."""
        return self.ending is not None

    def finish(self, result: str, winner_role: str | None, reason: str) -> None:
        """Record the ending exactly once."""
        if self.ending is None:
            self.ending = Ending(result, winner_role, reason)


def fresh_state(cfg: GameConfig, role: str) -> TurnState:
    """A brand-new per-sub-game state (fresh runtime rule — only the transport survives)."""
    start = cfg.cop_start if role == "police" else cfg.thief_start
    return TurnState(
        cfg=cfg,
        role=role,
        board=Board(cfg.grid_size),
        my_pos=start,
        barriers_left=cfg.max_barriers if role == "police" else 0,
    )


@dataclass
class SideKit:
    """The per-sub-game helpers: scent, tracker, hints, liar-score, metering."""

    flow: ScentFlow
    tracker: Tracker
    hints: HintProvider
    liar: LiarScore = field(default_factory=LiarScore)
    meter: HintMeter = field(default_factory=HintMeter)

    @classmethod
    def fresh(
        cls,
        cfg: GameConfig,
        role: str,
        *,
        seed: int,
        every_n: int = 1,
        lie_rate: float = 0.75,
        scent_model: str | None = None,
    ) -> SideKit:
        """Build the standard kit for one sub-game (template hints; Gemini attaches later)."""
        meter = HintMeter()
        model = scent_model or SUBTRACTIVE
        return cls(
            flow=ScentFlow(cfg, model),
            tracker=Tracker(exact_capable=model == SUBTRACTIVE),
            hints=HintProvider(
                role=role,
                arena=cfg.map_area,
                max_words=cfg.hint_max_words,
                every_n_steps=every_n,
                lie_rate=lie_rate,
                seed=seed,
            ),
            meter=meter,
        )


TurnRecord = dict[str, Any]
