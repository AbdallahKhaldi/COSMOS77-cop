"""The hint provider chain: bluff policy -> Gemini (per cadence) -> templates -> lint.

Every turn gets a hint line; Gemini is only consulted every ``every_n_steps`` (token thrift), and
its output is linted (15-word cap, digit-free) before it may cross the wire. The sealed ``intent``
flag is the pool the line actually came from — a bluff recorded as truth is tampering (§2.2).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .gemini import GeminiHinter
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
        gemini: GeminiHinter | None = None,
        every_n_steps: int = 1,
        lie_rate: float = 0.75,
        seed: int = 7,
    ) -> None:
        """Configure the chain; ``gemini=None`` means pure template mode (zero tokens)."""
        self.role = role
        self.arena = arena
        self.max_words = max_words
        self.gemini = gemini
        self.every_n_steps = max(1, every_n_steps)
        self.lie_rate = lie_rate
        self.rng = random.Random(seed)

    def hint_for_step(self, step: int, sub_game: int) -> HintResult:
        """Produce the hint + intent for *step* (1-based)."""
        intent = "lie" if self.rng.random() < self.lie_rate else "truth"
        text: str | None = None
        if self.gemini is not None and step % self.every_n_steps == 0:
            text = self.gemini.hint(
                role=self.role, arena=self.arena, intent=intent, sub_game=sub_game
            )
        if text is None:
            text = template_hint(self.role, intent, self.arena, self.rng)
        final = enforce(text, max_words=self.max_words, fallback=safe_line(self.arena))
        return HintResult(text=final, intent=intent)
