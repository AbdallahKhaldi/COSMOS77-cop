"""Watchdog (rule 7): monitor loop progress and perform a controlled rescue on stall."""

from __future__ import annotations

from collections.abc import Callable


class Watchdog:
    """Fires the rescue callback once when no heartbeat lands within the budget."""

    def __init__(self, timeout_s: float, rescue: Callable[[], None]) -> None:
        """Arm with the stall budget and a rescue action (persist state, flush logs)."""
        self.timeout_s = timeout_s
        self._rescue = rescue
        self._last_beat: float | None = None
        self.fired = False

    def beat(self, now: float) -> None:
        """Record loop progress."""
        self._last_beat = now

    def check(self, now: float) -> bool:
        """Evaluate the stall budget; run the rescue exactly once on expiry."""
        if self.fired or self._last_beat is None:
            return self.fired
        if now - self._last_beat >= self.timeout_s:
            self.fired = True
            self._rescue()
        return self.fired
