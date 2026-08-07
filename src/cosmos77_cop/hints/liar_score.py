"""Per-opponent hint-truthfulness score, calibrated against scent-derived ground truth (§4.1).

When the tracker knows the opponent's true cell, every directional hint is checkable: a claim of
"north" while they sit in the south half is a caught lie. The running score weights how much the
belief layer trusts their future hints; hints from a caught liar converge to near-zero weight.
"""

from __future__ import annotations

Coord = tuple[int, int]

_DIRECTION_WORDS: dict[str, str] = {
    "north": "north",
    "uptown": "north",
    "south": "south",
    "downtown": "south",
    "east": "east",
    "west": "west",
}


def hinted_direction(text: str) -> str | None:
    """The first compass direction the hint commits to, if any."""
    lowered = text.lower()
    for word, direction in _DIRECTION_WORDS.items():
        if word in lowered:
            return direction
    return None


def direction_matches(direction: str, cell: Coord, grid_size: int) -> bool:
    """Whether *cell* actually lies in the half the direction names (strict halves)."""
    half = grid_size / 2
    row, col = cell
    return {
        "north": row < half,
        "south": row >= half,
        "east": col >= half,
        "west": col < half,
    }[direction]


class LiarScore:
    """Exponentially-updated truthfulness in [0, 1]; 0.5 = uncalibrated."""

    def __init__(self, alpha: float = 0.3) -> None:
        """Start uncalibrated with smoothing *alpha*."""
        self.value = 0.5
        self.alpha = alpha
        self.observations = 0

    def observe(self, hint_text: str, true_cell: Coord, grid_size: int) -> None:
        """Score one hint against the opponent's known true cell (no-op when directionless)."""
        direction = hinted_direction(hint_text)
        if direction is None:
            return
        truthful = direction_matches(direction, true_cell, grid_size)
        self.value = (1 - self.alpha) * self.value + self.alpha * (1.0 if truthful else 0.0)
        self.observations += 1

    def weight(self) -> float:
        """How strongly a directional hint should condition the belief map (0..1)."""
        return self.value
