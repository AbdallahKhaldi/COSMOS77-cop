"""Audit layer 4: concession/answer corroboration for rule-46/47 endings (kit SPEC §2a).

A ``caught: true`` echoing the cop's claimed cell is an ANSWER (the trail must end there).
Naming any other cell is a CONCESSION (rule 46/47): the cell must be captured under the cop's
OWN barrier record — on a placed barrier (46) or boxed in by them (47) — and the trail must end
there. Failed corroboration voids the capture (settled ``tamper_forfeit``); never auto-believe.
"""

from __future__ import annotations

from typing import Any

from ..engine.board import Board

Coord = tuple[int, int]


def _cell(value: object) -> Coord | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (int(value[0]), int(value[1]))
    return None


def corroborate_capture(
    claim_response: dict[str, Any],
    *,
    trail_end: Coord | None,
    cop_claimed_cell: Coord | None,
    barrier_cells: set[Coord],
    grid_size: int,
) -> tuple[bool, str]:
    """Corroborate a ``caught: true`` final against our own records; (ok, reason)."""
    named = _cell(claim_response.get("claim"))
    if named is None or not claim_response.get("caught"):
        return False, "final response does not name a caught cell"
    if trail_end is not None and trail_end != named:
        return False, f"revealed trail ends at {trail_end}, not the conceded {named}"
    if cop_claimed_cell is not None and named == cop_claimed_cell:
        return True, "answer: echoes our co-location claim"
    if named in barrier_cells:
        return True, "concession corroborated: cell is under our rule-46 barrier"
    board = Board(grid_size, set(barrier_cells))
    if board.in_bounds(named) and not board.open_neighbors(named):
        return True, "concession corroborated: cell is boxed under our barriers (rule 47)"
    return False, f"conceded cell {named} matches neither our claim nor our barrier record"
