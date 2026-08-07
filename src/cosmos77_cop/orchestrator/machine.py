"""The per-sub-game state machine (rules 4-5): reference states, illegal transitions raise.

``WAITING_FOR_OPPONENT -> COMPUTING_MOVE -> COMMITTING -> AWAITING_REVEAL -> VERIFYING -> (loop)``
with the absorbing ``TECHNICAL_LOSS`` and the terminal ``DONE`` (a played ending).
"""

from __future__ import annotations

WAITING_FOR_OPPONENT = "WAITING_FOR_OPPONENT"
COMPUTING_MOVE = "COMPUTING_MOVE"
COMMITTING = "COMMITTING"
AWAITING_REVEAL = "AWAITING_REVEAL"
VERIFYING = "VERIFYING"
TECHNICAL_LOSS = "TECHNICAL_LOSS"
DONE = "DONE"

_ALLOWED: dict[str, tuple[str, ...]] = {
    WAITING_FOR_OPPONENT: (COMPUTING_MOVE, TECHNICAL_LOSS),
    COMPUTING_MOVE: (COMMITTING, TECHNICAL_LOSS),
    COMMITTING: (AWAITING_REVEAL, TECHNICAL_LOSS),
    AWAITING_REVEAL: (VERIFYING, TECHNICAL_LOSS),
    VERIFYING: (COMPUTING_MOVE, DONE, TECHNICAL_LOSS),
    TECHNICAL_LOSS: (),
    DONE: (),
}


class IllegalTransitionError(RuntimeError):
    """A state change the machine forbids (rule 5: reject every illegal transition)."""


class StateMachine:
    """One sub-game's lifecycle; ``TECHNICAL_LOSS`` and ``DONE`` absorb."""

    def __init__(self) -> None:
        """Every sub-game starts waiting for the opponent's handshake."""
        self.state = WAITING_FOR_OPPONENT
        self.history: list[str] = [WAITING_FOR_OPPONENT]

    def transition(self, target: str) -> str:
        """Move to *target* or raise :class:`IllegalTransitionError`."""
        if target not in _ALLOWED.get(self.state, ()):
            raise IllegalTransitionError(f"{self.state} -> {target} is not a legal transition")
        self.state = target
        self.history.append(target)
        return target

    @property
    def absorbed(self) -> bool:
        """True once the machine can never move again."""
        return not _ALLOWED[self.state]
