"""Per-step commit-reveal sealing (kit SPEC §3; rules 17-18).

``commit = SHA256(canonical_json(payload) + "|" + nonce)`` — the nonce is pipe-appended OUTSIDE
the JSON. The release prints three constructions; only this reference form binds the full record
(the ``divergent_forms`` vector tells them apart).
"""

from __future__ import annotations

import hashlib

from .canonical import canonical_str

VERDICT_MOVED = "moved"
VERDICT_BARRIER = "placed_barrier"
VERDICT_SETTLED = "settled"
INTENT_TRUTH = "truth"
INTENT_LIE = "lie"

Coord = tuple[int, int]


def commit(payload: dict[str, object], nonce: str) -> str:
    """Seal *payload* under *nonce*; the opponent re-hashes this exact construction at audit."""
    return hashlib.sha256(f"{canonical_str(payload)}|{nonce}".encode()).hexdigest()


def state_string(grid_size: int, self_pos: Coord, barriers: list[Coord]) -> str:
    """The reference ``state`` spelling: Python list reprs WITH the space after the comma."""
    cells = sorted([b[0], b[1]] for b in barriers)
    return f"grid={grid_size}x{grid_size};self={[self_pos[0], self_pos[1]]};barriers={cells}"


def build_turn_payload(
    *,
    step: int,
    role: str,
    sub_game: int,
    grid_size: int,
    self_pos: Coord,
    barriers: list[Coord],
    move: str,
    intent: str,
    hint: str,
    verdict: str,
) -> dict[str, object]:
    """Our sealed per-step record (kit shape; the schema itself is not an interop constraint)."""
    return {
        "step": step,
        "role": role,
        "sub_game": sub_game,
        "state": state_string(grid_size, self_pos, barriers),
        "position": [self_pos[0], self_pos[1]],
        "move": move,
        "intent": intent,
        "hint": hint,
        "verdict": verdict,
    }
