"""Doctor report assembly: stage verdicts, worst-of summary, ordered next actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..protocol.canonical import canonical_str

GREEN = "green"
YELLOW = "yellow"
RED = "red"

_SEVERITY = {GREEN: 0, YELLOW: 1, RED: 2}

STAGE_ORDER = ("reach", "contract", "locks", "handshake", "uid", "forensics", "topology")


@dataclass(frozen=True)
class Stage:
    """One stage's verdict: a status, a human finding, and an optional pasteable fix."""

    name: str
    status: str
    finding: str
    fix_line: str | None = None
    detail: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        """The stage as a JSON-ready mapping (``None`` fields dropped)."""
        body: dict[str, Any] = {"status": self.status, "finding": self.finding}
        if self.fix_line is not None:
            body["fix_line"] = self.fix_line
        if self.detail is not None:
            body["detail"] = self.detail
        return body


def skipped(name: str, why: str) -> Stage:
    """A stage that could not run for lack of input — green, explicitly labeled skipped."""
    return Stage(name, GREEN, f"skipped — {why}")


def worst(statuses: list[str]) -> str:
    """The most severe status in *statuses* (an empty list is green)."""
    return max(statuses, key=lambda s: _SEVERITY[s]) if statuses else GREEN


def next_actions(stages: list[Stage]) -> list[str]:
    """Ordered to-do list: red stages first, then yellow; fix_line preferred over finding."""
    flagged = [s for s in stages if s.status != GREEN]
    flagged.sort(key=lambda s: (-_SEVERITY[s.status], STAGE_ORDER.index(s.name)))
    actions = [f"[{s.name}] {s.fix_line or s.finding}" for s in flagged]
    return actions or ["ready: no blocking findings — agree a window and play"]


def build_report(
    *, stages: list[Stage], target: dict[str, Any], generated_by: str
) -> dict[str, Any]:
    """Compose the whole machine-readable report from the stage verdicts."""
    return {
        "doctor_version": 1,
        "generated_by": generated_by,
        "target": target,
        "stages": {s.name: s.to_json() for s in stages},
        "summary": {
            "status": worst([s.status for s in stages]),
            "next_actions": next_actions(stages),
        },
    }


def render(report: dict[str, Any]) -> str:
    """One line of canonical JSON — sorted keys, compact separators, raw UTF-8."""
    return canonical_str(report)
