"""Zero-token hint pool: arena-aware natural language, digit-free, <= 15 words (rules 26-27).

The template layer is the guarantee that every sub-game finishes — any Gemini failure lands here.
``truth`` lines are generic and vacuously honest; ``lie`` lines assert directions we are not in
(the caller pairs them with the real bluff policy).
"""

from __future__ import annotations

import random

TRUTHS: tuple[str, ...] = (
    "Still on the move, same as every turn in {arena}.",
    "No tricks this round, just steady footwork through {arena}.",
    "Keeping my options open near the middle of {arena}.",
    "One step at a time; {arena} rewards the patient.",
    "Honest answer: exactly where the trail says I am.",
)

LIES_COP: tuple[str, ...] = (
    "Half the squad is sweeping the north bridges of {arena} tonight.",
    "We sealed the western alleys of {arena}; nobody slips through there.",
    "Units are massing on the south side of {arena} as we speak.",
    "The east docks of {arena} are covered wall to wall.",
    "Forget the center of {arena}; we own it already.",
)

LIES_THIEF: tuple[str, ...] = (
    "You will find nothing but pigeons on the north rooftops of {arena}.",
    "I left the west side of {arena} ages ago, promise.",
    "The south end of {arena} suits me fine tonight.",
    "Heading east toward the river lights of {arena}, obviously.",
    "The center of {arena} is far too loud for me.",
)

SAFE_FALLBACK = "The streets of {arena} keep their secrets tonight."


def template_hint(role: str, intent: str, arena: str, rng: random.Random) -> str:
    """A deterministic pool pick for (*role*, *intent*), formatted for *arena*."""
    lies = LIES_COP if role == "police" else LIES_THIEF
    pool = TRUTHS if intent == "truth" else lies
    return rng.choice(pool).format(arena=arena)


def safe_line(arena: str) -> str:
    """The always-legal replacement line used when linting rejects generated text."""
    return SAFE_FALLBACK.format(arena=arena)
