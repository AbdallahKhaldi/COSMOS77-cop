"""ASGI entry for Render: ``uvicorn cosmos77_cop.net.asgi:app --host 0.0.0.0 --port $PORT``.

A bare browser GET at ``/mcp`` answers 406 — that IS the ready state (poll for it, never 200).
Tools-only until a peer dials in; the Phase-11B standing-friendly loop attaches here.
"""

from __future__ import annotations

from .server import PeerInbox, build_server

inbox = PeerInbox()
mcp = build_server(inbox, "cosmos77-cop")
app = mcp.http_app(path="/mcp")
