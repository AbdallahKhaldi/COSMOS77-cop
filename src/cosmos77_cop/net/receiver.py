"""The at-least-once receiver contract (kit SPEC §7.1, PROMOTED; delivery_contract vector).

HTTP retries deliver duplicates BY DESIGN. Decisions: dedupe on the COMMIT (never (kind, step));
same commit for a played step absorbs; a different commit is EQUIVOCATION and stays loud; the
reorder window IS the flood rule; below-next-never-played can never become applicable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

APPLY = "apply"
ABSORB = "absorb"
EQUIVOCATION = "equivocation"
BUFFER = "buffer"
VIOLATION = "violation"
DISCARD = "discard"


class BudgetError(ValueError):
    """Timing budgets that cannot work together (reconciled at load, not mid-game)."""


def reconcile_budgets(
    *,
    watchdog_s: float,
    poll_s: float,
    connect_timeout_s: float,
    turn_timeout_s: float,
    reorder_window: int,
) -> None:
    """Refuse impossible budget combinations before the first message ever arrives."""
    if watchdog_s <= 0:
        raise BudgetError("watchdog must be > 0")
    if poll_s >= watchdog_s:
        raise BudgetError("poll interval must be < watchdog")
    if connect_timeout_s > turn_timeout_s:
        raise BudgetError("connect timeout must be <= turn timeout")
    # io_stall (= turn + watchdog) > turn is implied by watchdog > 0 — documented, not re-checked.
    if reorder_window < 1:
        raise BudgetError("reorder window must be >= 1 (0 turns a retry race into a loss)")


@dataclass
class Receiver:
    """Step-ordered inbox for one peer's turn stream."""

    window: int = 4
    next_step: int = 1
    played: dict[int, str] = field(default_factory=dict)
    buffered: dict[int, dict[str, Any]] = field(default_factory=dict)
    equivocations: list[tuple[int, str, str]] = field(default_factory=list)
    violations: list[int] = field(default_factory=list)

    def decide(self, step: int, commit: str) -> str:
        """The pure decision function over the current state (delivery_contract table)."""
        if step in self.played:
            return ABSORB if self.played[step] == commit else EQUIVOCATION
        if step == self.next_step:
            return APPLY
        if self.next_step < step <= self.next_step + self.window:
            return BUFFER
        if step > self.next_step + self.window:
            return VIOLATION
        return DISCARD

    def ingest(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        """Feed one arrival; return the messages that became applicable, in step order."""
        step, commit = int(message["step"]), str(message["commit"])
        decision = self.decide(step, commit)
        if decision == EQUIVOCATION:
            self.equivocations.append((step, self.played[step], commit))
            return []
        if decision == VIOLATION:
            self.violations.append(step)
            return []
        if decision in (ABSORB, DISCARD):
            return []
        if decision == BUFFER:
            self.buffered.setdefault(step, message)
            return []
        applied = [message]
        self.played[step] = commit
        self.next_step += 1
        while self.next_step in self.buffered:
            nxt = self.buffered.pop(self.next_step)
            self.played[self.next_step] = str(nxt["commit"])
            applied.append(nxt)
            self.next_step += 1
        return applied
