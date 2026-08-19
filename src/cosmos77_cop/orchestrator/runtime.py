"""Shared live-wire runtime: handshake exchange, routed awaits, audit exchange.

Used by the smoke gate, the sub-game loop, and the series driver. All deadlines are hard; all
inbound traffic is routed through the receiver contract regardless of loop phase (a turn arriving
during a handshake is buffered knowledge, never dropped).
"""

from __future__ import annotations

import threading
import time
from typing import Any

import uvicorn

from ..crypto.nonce import new_nonce
from ..net.client import PeerCallError
from ..net.server import KIND_AUDIT, KIND_NEGOTIATE, KIND_TURN
from ..net.wire import refuse_turn
from .dialect import greeting_from_reply
from .gateway import Gateway


def start_server(mcp: object, port: int, host: str = "127.0.0.1") -> uvicorn.Server:
    """Serve the MCP app in a daemon thread; block until ready.

    Loopback-bound, ``serve --port 8801`` answers ourselves and refuses the LAN — the
    opponent sees connection refused while every local probe says we are healthy.  So
    ``serve`` binds 0.0.0.0 and selfplay stays on loopback.
    """
    config = uvicorn.Config(
        mcp.http_app(path="/mcp"), host=host, port=port, log_level="info"
    )
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 15.0
    while not server.started:
        if time.monotonic() > deadline:  # port held / bind refused: fail loudly, never hang
            raise RuntimeError(f"MCP server failed to bind {host}:{port} within 15s")
        time.sleep(0.02)
    return server


def route_turn(gateway: Gateway, message: dict[str, Any]) -> list[dict[str, Any]]:
    """Route one wire turn; nonconformant ones are refused with a reason (net/wire.py)."""
    if (reason := refuse_turn(message)) is not None:
        gateway.receiver.malformed += 1
        print(f"turn refused: {reason}")
        return []
    try:
        applied = gateway.receiver.ingest(message)
    except (KeyError, TypeError, ValueError):
        gateway.receiver.malformed += 1
        return []
    for msg in applied:
        gateway.received_commits[int(msg["step"])] = str(msg["commit"])
    return applied


def handshake(gateway: Gateway) -> bool:
    """Re-greet on a cadence until verified both ways.

    Greetings are idempotent; one lost to a drain or a late-started peer must never
    deadlock the window.
    """
    deadline = time.monotonic() + gateway.peer_cfg.handshake_budget_s
    sent = verified = False
    last_send = -10.0
    while time.monotonic() < deadline and not (sent and verified):
        now = time.monotonic()
        if now - last_send >= (2.0 if sent else 0.5):
            try:
                reply = gateway.client.call(
                    "negotiate", {"message": gateway.greeting(new_nonce())},
                    deadline_s=max(5.0, gateway.peer_cfg.connect_timeout_s),
                )
                sent = True
                if not verified:
                    verified = greeting_from_reply(gateway, reply)
            except PeerCallError:
                pass
            last_send = now
        if gateway.pending_greetings:
            item = (KIND_NEGOTIATE, gateway.pending_greetings.pop(0))
        else:
            item = gateway.inbox.pull(timeout_s=0.2)
        if item and item[0] == KIND_TURN:
            gateway.pending_turns.extend(route_turn(gateway, item[1]))
        elif item and item[0] == KIND_AUDIT:
            gateway.pending_audits.append(item[1])
        elif item and item[0] == KIND_NEGOTIATE:
            verdict = gateway.verify(item[1])
            if verdict.ok:
                gateway.peer_greeting = item[1]
                verified = True
            elif not verdict.bystander:
                print(f"handshake refused: {verdict.code} {verdict.detail}")
                return False
    return sent and verified


def await_applied(gateway: Gateway, timeout_s: float) -> list[dict[str, Any]]:
    """Wait for the next applied opponent turn(s); [] on deadline expiry (never a hang)."""
    if gateway.pending_turns:
        batch, gateway.pending_turns = gateway.pending_turns, []
        return batch
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        item = gateway.inbox.pull(timeout_s=gateway.peer_cfg.poll_s)
        if item and item[0] == KIND_TURN:
            applied = route_turn(gateway, item[1])
            if applied:
                return applied
        elif item and item[0] == KIND_AUDIT:
            gateway.pending_audits.append(item[1])
        elif item and item[0] == KIND_NEGOTIATE:
            gateway.pending_greetings.append(item[1])
    return []


# Delivery moved to .delivery; re-exported so call sites and test patches keep one seam.
from .delivery import exchange_audits, send_turn  # noqa: E402

__all__ = ["await_applied", "exchange_audits", "handshake", "route_turn",
           "send_turn", "start_server"]
