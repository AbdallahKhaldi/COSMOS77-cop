"""Replay verification: recompute the FULL sealed commit for every revealed step (rule 20).

The book's simplified ``nonce|move`` sketch will not reproduce a real commit — the viewer must
re-hash the whole sealed payload with the pinned construction (playbook §7.20). One failure voids
the match, so the per-step verdict is what the viewer stamps on screen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..protocol.sealing import commit

VERIFIED = "Verified OK"
TAMPERED = "TAMPERED"


@dataclass(frozen=True)
class StepVerdict:
    """One revealed record, re-hashed."""

    index: int
    step: int
    side: str
    ok: bool
    declared: str
    recomputed: str
    payload: dict[str, Any]

    @property
    def stamp(self) -> str:
        """The words the viewer prints."""
        return VERIFIED if self.ok else TAMPERED


@dataclass(frozen=True)
class ReplayResult:
    """A whole log, verified."""

    path: str
    verdicts: tuple[StepVerdict, ...]
    summary: dict[str, Any]

    @property
    def clean(self) -> bool:
        """True when every revealed record re-hashes to its own commit."""
        return all(v.ok for v in self.verdicts)

    @property
    def stamp(self) -> str:
        """The banner for the whole log."""
        return VERIFIED if self.clean else TAMPERED

    @property
    def failures(self) -> tuple[StepVerdict, ...]:
        """Only the records that failed."""
        return tuple(v for v in self.verdicts if not v.ok)


def verify_records(records: list[dict[str, Any]], side: str, start: int = 0) -> list[StepVerdict]:
    """Re-hash each ``{payload, nonce, commit}`` record with our own serializer."""
    verdicts = []
    for offset, record in enumerate(records):
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        declared = str(record.get("commit", ""))
        recomputed = commit(payload, str(record.get("nonce", "")))
        verdicts.append(
            StepVerdict(
                index=start + offset,
                step=int(payload.get("step", -1)),
                side=side,
                ok=recomputed == declared,
                declared=declared,
                recomputed=recomputed,
                payload=payload,
            )
        )
    return verdicts


def verify_log(path: str | Path) -> ReplayResult:
    """Load a ``log_*.json`` and verify every revealed record on both sides."""
    log = json.loads(Path(path).read_text(encoding="utf-8"))
    ours = verify_records(list(log.get("records") or []), "ours")
    theirs = verify_records(list(log.get("opponent_records") or []), "opponent", len(ours))
    return ReplayResult(
        path=str(path), verdicts=tuple(ours + theirs), summary=dict(log.get("summary") or {})
    )
