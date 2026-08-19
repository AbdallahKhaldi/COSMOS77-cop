"""The wire monitor: one line per MCP call, both directions, visible everywhere.

Five real league windows were diagnosed blind: the operator watching the arena saw
NOTHING move and had no way to see who dialed whom, and the run logs recorded only
the settle line.  Every outbound call and inbound tool hit now emits one compact
line to stdout (captured into the run log the admin panel and `railway ssh tail -f`
read) and, when an events sink is wired, one ``{"t": "wire"}`` JSON line that the
hub streams live into the arena's strip.  Faults never escape — monitoring must not
add a failure mode to a real game.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

TAP: Callable[[dict[str, Any]], None] | None = None  # set by serve when --events is on


def emit(direction: str, tool: str, peer: str, status: str, ms: float | None = None) -> None:
    """Record one wire event: ``direction`` is ``out`` (we dialed) or ``in`` (they did)."""
    try:
        arrow = "->" if direction == "out" else "<-"
        stamp = time.strftime("%H:%M:%S", time.gmtime())
        took = f" {ms:.0f}ms" if ms is not None else ""
        print(f"wire {stamp} {arrow} {tool} @{peer} {status}{took}", flush=True)
        if TAP is not None:
            TAP({"t": "wire", "direction": direction, "tool": tool, "peer": peer,
                 "status": status, "ms": round(ms, 1) if ms is not None else None})
    except Exception:
        pass
