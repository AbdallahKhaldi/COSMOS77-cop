"""Per-turn JSONL event stream — the hub viewer's data source, LOCAL TRUTH ONLY.

One line is appended per ``on_view`` callback, so the file is exactly the sequence of moments
the mandated live GUI draws (rules 8-9: our own state and our own inference, never the
opponent's true position). The sink runs synchronously inside the turn loop, so it must never
add a failure mode to a real game: every write is append+flush, and every error is swallowed
and counted, never raised.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVENTS_FILENAME = "events.jsonl"


def view_line(view: object) -> dict[str, Any]:
    """One event dict for one :class:`~cosmos77_cop.gui.model.LiveView` — exactly its fields."""
    return {
        "t": "view",
        "role": view.role,
        "sub_game": view.sub_game,
        "step": view.step,
        "banner": view.banner,
        "self_pos": list(view.self_pos),
        "barriers": sorted(list(b) for b in view.barriers),
        "barriers_left": view.barriers_left,
        "posterior": {f"{r},{c}": p for (r, c), p in view.posterior.items()},
        "perceived_scent": {f"{r},{c}": v for (r, c), v in view.perceived_scent.items()},
        "confidence": view.confidence,
        "hints": list(view.hints),
    }


class EventSink:
    """Appends one JSON line per view to ``<out>/events.jsonl``; faults never escape."""

    def __init__(self, out_dir: str | Path) -> None:
        """Bind the stream to *out_dir* (created lazily on the first write)."""
        self.path = Path(out_dir) / EVENTS_FILENAME
        self.errors = 0

    @classmethod
    def tapped(cls, out_dir: str | Path) -> EventSink:
        """A sink with the wire monitor plugged in — serve/selfplay's constructor."""
        from ..net import wiretap
        from ..orchestrator.brainbridge import ROLE

        sink = cls(out_dir)
        wiretap.TAP = sink.wire
        wiretap.WHO = ROLE  # f2 shares ONE stream between both our roles — tag the speaker
        return sink

    def update(self, view: object) -> None:
        """Duck-typed window sink: append *view* as one flushed JSON line."""
        try:
            line = json.dumps(view_line(view), sort_keys=True, separators=(",", ":"))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
                stream.flush()
        except Exception:  # the turn loop must never see a viewer fault
            self.errors += 1

    def wire(self, event: dict[str, Any]) -> None:
        """Append one wire-monitor line (same file, same never-fail contract)."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
                stream.flush()
        except Exception:
            self.errors += 1
