"""Settlement: one rule for every sub-game ending (kit SPEC §9; playbook §2.9).

Audits exchanged and clean -> the played outcome stands. Exchanged and failed -> TAMPER_FORFEIT
(the failed audit IS the settlement). No audit on a zeroed outcome -> the pair-agreed
technical-loss row. No audit on a PLAYED outcome -> NOT settled: no result artifact, nothing is
sent — and all six sub-games are finished regardless.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..protocol.outcome import ZEROED
from .audit import AuditReport


@dataclass(frozen=True)
class Settlement:
    """How a sub-game row settles into the result artifact (or refuses to)."""

    settled: bool
    result: str | None
    log_verified: bool
    tampered: bool


def settled_outcome(
    played_result: str,
    my_audit_of_them: AuditReport | None,
    their_audit_arrived: bool,
) -> Settlement:
    """Apply the settlement rule to one sub-game."""
    if my_audit_of_them is not None and their_audit_arrived:
        if my_audit_of_them.clean:
            return Settlement(True, played_result, log_verified=True, tampered=False)
        return Settlement(True, "tamper_forfeit", log_verified=False, tampered=True)
    if played_result in ZEROED:
        return Settlement(True, played_result, log_verified=False, tampered=False)
    return Settlement(False, None, log_verified=False, tampered=False)
