"""The hint chain: bluff policy -> Gemini (cadence AND budget) -> templates -> lint -> measure.

Every turn gets a hint line; Gemini is only consulted every ``every_n_steps`` (token thrift) and
only while the series is still inside the negotiated ``token_budget_per_series`` (rule 54), and
its output is linted (word cap, digit-free) before it may cross the wire. The sealed ``intent``
flag is then MEASURED against the line that actually crosses the wire and the cell we actually
seal — never drawn from an RNG before the text exists. A bluff recorded as truth is tampering
(§2.2); a truth recorded as a bluff hands a peer our real half for nothing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..engine.board import Coord
from .gemini import GeminiHinter
from .liar_score import declared_intent
from .lint import enforce
from .templates import safe_line, template_hint


@dataclass(frozen=True)
class HintResult:
    """The wire hint text and the truthfully-declared intent that seals with it."""

    text: str
    intent: str


class HintProvider:
    """Deterministic (seeded) hint production for one sub-game."""

    def __init__(
        self,
        *,
        role: str,
        arena: str,
        max_words: int,
        grid_size: int,
        token_budget: int,
        gemini: GeminiHinter | None = None,
        every_n_steps: int = 1,
        lie_rate: float = 0.75,
        seed: int = 7,
    ) -> None:
        """Configure the chain; ``gemini=None`` means pure template mode (zero tokens)."""
        self.role = role
        self.arena = arena
        self.max_words = max_words
        self.grid_size = grid_size
        self.token_budget = token_budget
        self.gemini = gemini
        self.every_n_steps = max(1, every_n_steps)
        self.lie_rate = lie_rate
        self.rng = random.Random(seed)

    def _may_generate(self, step: int) -> bool:
        """Cadence AND budget: the negotiated series budget is a hard stop, not a target.

        The meter carries what earlier sub-games of this series already spent, so a fresh
        per-sub-game kit cannot silently restart the allowance.
        """
        if self.gemini is None or step % self.every_n_steps != 0:
            return False
        return self.gemini.meter.series_total < self.token_budget

    def hint_for_step(self, step: int, sub_game: int, *, cell: Coord) -> HintResult:
        """The hint for *step* (1-based) and the intent it may honestly be sealed with."""
        bluff = "lie" if self.rng.random() < self.lie_rate else "truth"
        text: str | None = None
        if self._may_generate(step):
            text = self.gemini.hint(
                role=self.role, arena=self.arena, intent=bluff,
                sub_game=sub_game, max_words=self.max_words,
            )
        if text is None:
            text = template_hint(self.role, bluff, self.arena, self.rng)
        final = enforce(text, max_words=self.max_words, fallback=safe_line(self.arena))
        return HintResult(text=final, intent=declared_intent(final, cell, self.grid_size, bluff))
