"""The four MCP tools with the reference's exact names and argument asymmetry (SPEC §8).

Every handler validates shape, enqueues, and returns ``{"ok": True}`` IMMEDIATELY — the game loop
runs on a worker thread. A refusal can never be a return value; it travels as a ControlMessage.
``submit_audit`` takes ``payload``; the other three take ``message``.
"""

from __future__ import annotations

import queue
from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP

from . import wiretap

KIND_NEGOTIATE = "negotiate"
KIND_TURN = "turn"
KIND_CONTROL = "control"
KIND_AUDIT = "audit"

OK: dict[str, bool] = {"ok": True}


class PeerInbox:
    """Thread-safe queue between the transport handlers and the game loop."""

    def __init__(self, maxsize: int = 100) -> None:
        """Bound the queue at the constitution's queue depth (overflow drops, counted)."""
        self._queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue(maxsize=maxsize)
        self.dropped = 0

    def push(self, kind: str, payload: object) -> None:
        """Enqueue a shape-valid message; junk and overflow are dropped, never raised."""
        if not isinstance(payload, dict):
            self.dropped += 1
            return
        try:
            self._queue.put_nowait((kind, payload))
        except queue.Full:
            self.dropped += 1

    def pull(self, timeout_s: float) -> tuple[str, dict[str, Any]] | None:
        """Dequeue the next message or ``None`` after *timeout_s* (one poll lap)."""
        try:
            return self._queue.get(timeout=timeout_s)
        except queue.Empty:
            return None


def build_server(
    inbox: PeerInbox, name: str, greeting_provider: Callable[[], dict | None] | None = None
) -> FastMCP:
    """The FastMCP app exposing negotiate / receive_turn / receive_control / submit_audit.

    ``negotiate`` answers with OUR greeting under ``message`` when a provider is wired.
    The kit's wire surface leaves the direction open ("either side may open"), and its
    WARNINGS 2b documents two live stalls where a push peer and a request/response peer
    were each conformant and mutually mute.  Carrying the greeting in the reply makes a
    request/response opponent read the agreement out of its own call; push opponents
    ignore the extra key (the extension seam).  Still validate -> enqueue -> return
    immediately: the provider is pure construction, never I/O.
    """
    mcp: FastMCP = FastMCP(name)

    @mcp.tool
    def negotiate(message: dict) -> dict:
        """Receive the opponent's greeting (terms, signature, pairing, locks, uid)."""
        wiretap.emit("in", "negotiate", str((message or {}).get("group_id", "?")), "recv")
        inbox.push(KIND_NEGOTIATE, message)
        greeting = greeting_provider() if greeting_provider is not None else None
        if greeting is not None:
            return {**OK, "message": greeting}
        return OK

    @mcp.tool
    def receive_turn(message: dict) -> dict:
        """Receive one sealed half-turn (commit + hint + smell_grid + declarations)."""
        wiretap.emit("in", "receive_turn",
                     f"step {(message or {}).get('step', '?')} {(message or {}).get('sender', '')}",
                     "recv")
        inbox.push(KIND_TURN, message)
        return OK

    @mcp.tool
    def receive_control(message: dict) -> dict:
        """Receive an out-of-band control message (refusals, status, restart, quit)."""
        inbox.push(KIND_CONTROL, message)
        return OK

    @mcp.tool
    def submit_audit(payload: dict) -> dict:
        """Receive the opponent's end-of-game reveal (records + nonces + result claim)."""
        wiretap.emit("in", "submit_audit",
                     f"{len((payload or {}).get('records') or [])} records", "recv")
        inbox.push(KIND_AUDIT, payload)
        return OK

    return mcp
