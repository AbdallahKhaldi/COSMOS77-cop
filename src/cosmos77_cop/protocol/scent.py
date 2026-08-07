"""Both registered scent models, byte-exact to the kit vectors (rule 23; SPEC §5 + §5.1).

``subtractive_chebyshev_v1`` (reference, transmitted): radial emit over the grid window,
subtractive decay, 3-decimal rounding. ``multiplicative_book_v1`` (book ch.4, not transmitted):
verbatim 5x5 kernel lookup, ``tau' = clamp((1 - rho) * tau + delta, 0, 0.9)`` once per full turn,
NO rounding, evaluation order exactly as written (IEEE-754 differs on the algebraic twin).
"""

from __future__ import annotations

Coord = tuple[int, int]

BOOK_KERNEL: tuple[tuple[float, ...], ...] = (
    (0.04, 0.14, 0.2, 0.14, 0.04),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.2, 0.62, 0.9, 0.62, 0.2),
    (0.14, 0.42, 0.62, 0.42, 0.14),
    (0.04, 0.14, 0.2, 0.14, 0.04),
)
BOOK_CLAMP_TOP = 0.9


def smell_emit(
    center: Coord, intensity: float, grid_size: int, board_size: int
) -> dict[str, float]:
    """``subtractive_chebyshev_v1`` emission: in-bounds cells with value > 0, keyed ``"r,c"``."""
    half = grid_size // 2
    falloff = intensity / (half + 1)
    field: dict[str, float] = {}
    for dr in range(-half, half + 1):
        for dc in range(-half, half + 1):
            r, c = center[0] + dr, center[1] + dc
            if not (0 <= r < board_size and 0 <= c < board_size):
                continue
            value = round(max(0.0, intensity - falloff * max(abs(dr), abs(dc))), 3)
            if value > 0:
                field[f"{r},{c}"] = value
    return field


def smell_decay(values: dict[str, float], decay: float) -> dict[str, float]:
    """One game-step of subtractive decay; keys are kept even at the 0.0 floor."""
    return {k: round(max(0.0, v - decay), 3) for k, v in values.items()}


def merge_max(trail: dict[str, float], emitted: dict[str, float]) -> dict[str, float]:
    """Merge a fresh emission into the trail cell-wise by max."""
    merged = dict(trail)
    for key, value in emitted.items():
        merged[key] = max(merged.get(key, 0.0), value)
    return merged


def book_delta(center: Coord, board_size: int) -> dict[Coord, float]:
    """``multiplicative_book_v1`` deposit: the verbatim kernel window clipped to the board."""
    half = len(BOOK_KERNEL) // 2
    delta: dict[Coord, float] = {}
    for dr in range(-half, half + 1):
        for dc in range(-half, half + 1):
            r, c = center[0] + dr, center[1] + dc
            if 0 <= r < board_size and 0 <= c < board_size:
                delta[(r, c)] = BOOK_KERNEL[dr + half][dc + half]
    return delta


def book_update(tau: float, delta: float, rho: float) -> float:
    """One full-turn update, evaluation order exactly as written: ``(1 - rho) * tau + delta``."""
    value = (1 - rho) * tau + delta
    return min(max(value, 0.0), BOOK_CLAMP_TOP)


def book_update_field(
    field: dict[Coord, float], delta: dict[Coord, float], rho: float
) -> dict[Coord, float]:
    """Apply one full-turn update over the union of the current field and the deposit window."""
    cells = set(field) | set(delta)
    return {c: book_update(field.get(c, 0.0), delta.get(c, 0.0), rho) for c in cells}
