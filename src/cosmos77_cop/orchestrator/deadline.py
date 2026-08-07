"""One clock per expected message (rule 6; delivery_contract deadline table).

Tolerated traffic never renews the deadline, and the clock is evaluated on EVERY loop lap —
a receiver that only checks on empty polls never checks under a flood.
"""

from __future__ import annotations

WAITING = "waiting"
EXPIRED = "expired"


class DeadlineClock:
    """Tracks the single deadline for the one message we are currently owed."""

    def __init__(self, deadline_at: float) -> None:
        """Arm the clock for one expected message."""
        self.deadline_at = deadline_at

    def lap(self, now: float, *, arrived: bool = False, tolerated: bool = False) -> str:
        """Evaluate the clock this lap; arrivals of tolerated traffic never move it."""
        del arrived, tolerated
        return EXPIRED if now >= self.deadline_at else WAITING

    def rearm(self, deadline_at: float) -> None:
        """Start the clock for the NEXT expected message (only after the current one applied)."""
        self.deadline_at = deadline_at
