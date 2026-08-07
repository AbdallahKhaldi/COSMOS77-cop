"""Legal movement and barrier-placement rules (rules 13-16 · playbook §0.5)."""

from __future__ import annotations

from .board import Board, Coord

MOVE_DELTAS: dict[str, Coord] = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
    "STAY": (0, 0),
}


class IllegalMoveError(ValueError):
    """A move that rules 13-14 or the board reject (diagonal, off-board, into a barrier)."""


def destination(pos: Coord, token: str) -> Coord:
    """The cell *token* leads to from *pos*; raise :class:`IllegalMoveError` on an unknown token."""
    try:
        delta = MOVE_DELTAS[token]
    except KeyError as exc:
        raise IllegalMoveError(f"unknown move token {token!r} (orthogonal + STAY only)") from exc
    return (pos[0] + delta[0], pos[1] + delta[1])


def legal_move_tokens(board: Board, pos: Coord) -> list[str]:
    """Every token legal from *pos*: STAY always, plus each open orthogonal step."""
    return [t for t in MOVE_DELTAS if t == "STAY" or board.is_open(destination(pos, t))]


def apply_move(board: Board, pos: Coord, token: str) -> Coord:
    """Validate and apply *token* from *pos*, returning the new cell."""
    dest = destination(pos, token)
    if token != "STAY" and not board.is_open(dest):
        reason = "off-board" if not board.in_bounds(dest) else "into a barrier"
        raise IllegalMoveError(f"move {token} from {pos} is {reason}")
    return dest


def is_orthostep(src: Coord, dst: Coord) -> bool:
    """True when *src*→*dst* is a legal step shape: same cell or one orthogonal step.

    Used by the audit's physics layer (§2.8), which judges revealed position trails —
    never the peer's move-token spelling.
    """
    return abs(src[0] - dst[0]) + abs(src[1] - dst[1]) <= 1


def legal_barrier_cells(board: Board, cop_pos: Coord) -> set[Coord]:
    """Cells the cop may barrier this turn: its own cell or an open 4-neighbor (rule 15)."""
    return {cop_pos} | set(board.open_neighbors(cop_pos))


def validate_barrier_placement(board: Board, cop_pos: Coord, cell: Coord) -> None:
    """Raise :class:`IllegalMoveError` unless *cell* is a legal placement from *cop_pos*."""
    if cell not in legal_barrier_cells(board, cop_pos):
        raise IllegalMoveError(f"barrier {cell} is not the cop's cell or an open 4-neighbor")
