"""The three capture families (co-location · rule 46 · rule 47) and the concession payload."""

from __future__ import annotations

from .board import Board, Coord
from .rules import legal_move_tokens


def is_co_location(cop: Coord, thief: Coord) -> bool:
    """Family 1: the two agents occupy the same cell (cop claims, thief must answer truly)."""
    return cop == thief


def is_rule46(placed_cell: Coord, thief: Coord) -> bool:
    """Family 2: a barrier landed on the thief's current cell — capture (rule 46)."""
    return placed_cell == thief


def is_rule47_boxed(board: Board, thief: Coord) -> bool:
    """Family 3: the thief has no legal move besides STAY — captured (rule 47).

    STAY never rescues a fully-surrounded thief: boxed-in means every orthogonal
    neighbor is off-board or barriered.
    """
    return legal_move_tokens(board, thief) == ["STAY"]


def concession_payload(thief_cell: Coord) -> dict[str, object]:
    """The wire shape a thief MUST send for a rule-46/47 ending it alone can see.

    Naming its own final cell (rather than echoing a cop claim) marks this as a
    concession; the cop corroborates it at audit against its own barrier record.
    """
    return {"claim": [thief_cell[0], thief_cell[1]], "caught": True}
