"""End-of-game audit, layers 1-3 (rules 19 + 36; kit SPEC §9): integrity, binding, physics.

TAMPERED (a hash lie) is kept apart from ILLEGAL (impossible physics) so an honest team is never
sent hunting a serialization bug it does not have. A reveal with no position fields is a legal
degraded schema — verify what the evidence supports, note the rest, never accuse.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from ..protocol.sealing import VERDICT_BARRIER, commit

VERDICT_VERIFIED = "verified"
VERDICT_TAMPERED = "tampered"
VERDICT_ILLEGAL = "illegal"


@dataclass(frozen=True)
class AuditReport:
    """The audit's outcome: one verdict, the failing steps, and human-readable notes."""

    verdict: str
    failed_steps: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """True when the revealed log is fully verified."""
        return self.verdict == VERDICT_VERIFIED


def _integrity(records: list[dict[str, Any]]) -> tuple[list[int], list[str]]:
    failed, notes = [], []
    for record in records:
        step = int(record.get("payload", {}).get("step", -1))
        if commit(record.get("payload", {}), str(record.get("nonce", ""))) != record.get("commit"):
            failed.append(step)
            notes.append(f"step {step}: revealed (payload, nonce) does not re-hash to its commit")
    return failed, notes


def _binding(
    records: list[dict[str, Any]], received: dict[int, str]
) -> tuple[list[int], list[str]]:
    revealed = {int(r["payload"]["step"]): str(r["commit"]) for r in records if "payload" in r}
    failed, notes = [], []
    for step, wire_commit in received.items():
        if step not in revealed:
            failed.append(step)
            notes.append(f"step {step}: received in play but never revealed")
        elif revealed[step] != wire_commit:
            failed.append(step)
            notes.append(f"step {step}: revealed commit differs from the one received in play")
    return failed, notes


def _physics(
    records: list[dict[str, Any]], *, grid_size: int, barriers_max: int, max_steps: int
) -> tuple[list[int], list[str]]:
    rows = sorted(
        (r["payload"] for r in records if isinstance(r.get("payload"), dict)),
        key=lambda p: int(p.get("step", 0)),
    )
    positions = [(int(p["step"]), p["position"]) for p in rows if "position" in p]
    failed: list[int] = []
    notes: list[str] = []
    if not positions:
        note = "no position fields revealed - physics skipped (legal degraded schema)"
        return failed, [note]
    for step, pos in positions:
        r, c = int(pos[0]), int(pos[1])
        if not (0 <= r < grid_size and 0 <= c < grid_size):
            failed.append(step)
            notes.append(f"step {step}: position {pos} is off-board")
    for (_s1, p1), (s2, p2) in itertools.pairwise(positions):
        if abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) > 1:
            failed.append(s2)
            notes.append(f"step {s2}: {p1} -> {p2} is not one orthogonal step or STAY")
    placed = sum(1 for p in rows if p.get("verdict") == VERDICT_BARRIER)
    if placed > barriers_max:
        failed.append(-1)
        notes.append(f"{placed} barrier placements exceed the quota of {barriers_max}")
    top = max(int(p.get("step", 0)) for p in rows)
    if top > max_steps + 1:
        failed.append(top)
        notes.append(f"step {top} exceeds the ceiling {max_steps} (+1 terminal allowance)")
    return failed, notes


def audit_records(
    records: list[dict[str, Any]],
    received_commits: dict[int, str],
    *,
    grid_size: int,
    barriers_max: int,
    max_steps: int,
) -> AuditReport:
    """Run layers 1-3 over a revealed log; layer 4 (ending corroboration) is ``corroborate.py``."""
    tamper_steps, notes = _integrity(records)
    bind_steps, bind_notes = _binding(records, received_commits)
    tamper_steps += bind_steps
    notes += bind_notes
    if tamper_steps:
        return AuditReport(VERDICT_TAMPERED, sorted(set(tamper_steps)), notes)
    physics_steps, physics_notes = _physics(
        records, grid_size=grid_size, barriers_max=barriers_max, max_steps=max_steps
    )
    notes += physics_notes
    if physics_steps:
        return AuditReport(VERDICT_ILLEGAL, sorted(set(physics_steps)), notes)
    return AuditReport(VERDICT_VERIFIED, [], notes)
