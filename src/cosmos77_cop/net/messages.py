"""Wire message shapes (reference-v3): turn, control, audit (kit SPEC §8).

Turn messages emit nulls explicitly and receivers tolerate either. The timestamp rides the
message and stays OUT of the sealed payload — but it is never left empty (a reference-pinned
receiver may refuse an empty one).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

CONTROL_KINDS = ("enable", "status", "restart", "quit")
RESULT_CLAIMS = ("capture", "survival", "timeout")


def now_iso() -> str:
    """ISO-8601 UTC, second precision — the wire timestamp."""
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class TurnMessage:
    """One half-turn: the sealed commit plus everything public (hint, scent, declarations)."""

    step: int
    sender: str
    commit: str
    hint: str
    smell_grid: dict[str, float]
    timestamp: str
    barrier_placed: list[int] | None = None
    capture_claim: list[int] | None = None
    claim_response: dict[str, Any] | None = None
    win_claim: dict[str, Any] | None = None

    def to_wire(self) -> dict[str, Any]:
        """Full wire dict with explicit nulls."""
        return {
            "step": self.step,
            "sender": self.sender,
            "commit": self.commit,
            "hint": self.hint,
            "smell_grid": self.smell_grid,
            "timestamp": self.timestamp,
            "barrier_placed": self.barrier_placed,
            "capture_claim": self.capture_claim,
            "claim_response": self.claim_response,
            "win_claim": self.win_claim,
        }

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> TurnMessage:
        """Tolerant parse: extra keys ignored, absent optionals default to None."""
        return cls(
            step=int(raw["step"]),
            sender=str(raw["sender"]),
            commit=str(raw["commit"]),
            hint=str(raw.get("hint", "")),
            smell_grid=dict(raw.get("smell_grid") or {}),
            timestamp=str(raw.get("timestamp", "")),
            barrier_placed=raw.get("barrier_placed"),
            capture_claim=raw.get("capture_claim"),
            claim_response=raw.get("claim_response"),
            win_claim=raw.get("win_claim"),
        )


@dataclass(frozen=True)
class ControlMessage:
    """Out-of-band control: refusals, status, restarts — never a tool return value."""

    kind: str
    sender: str
    sub_game_number: int | None = None
    status: str | None = None
    step_budget: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        """Full wire dict with explicit nulls."""
        return {
            "kind": self.kind,
            "sender": self.sender,
            "sub_game_number": self.sub_game_number,
            "status": self.status,
            "step_budget": self.step_budget,
            "payload": self.payload,
        }

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> ControlMessage:
        """Tolerant parse of an inbound control message."""
        return cls(
            kind=str(raw.get("kind", "")),
            sender=str(raw.get("sender", "")),
            sub_game_number=raw.get("sub_game_number"),
            status=raw.get("status"),
            step_budget=raw.get("step_budget"),
            payload=dict(raw.get("payload") or {}),
        )


@dataclass(frozen=True)
class AuditPayload:
    """The end-of-game reveal: every sealed record with its nonce, plus our result claim."""

    sender: str
    records: list[dict[str, Any]]
    result_claim: str

    def to_wire(self) -> dict[str, Any]:
        """Full wire dict."""
        return {"sender": self.sender, "records": self.records, "result_claim": self.result_claim}

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> AuditPayload:
        """Tolerant parse of an inbound audit payload."""
        return cls(
            sender=str(raw.get("sender", "")),
            records=list(raw.get("records") or []),
            result_claim=str(raw.get("result_claim", "")),
        )
