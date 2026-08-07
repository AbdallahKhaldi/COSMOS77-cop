#!/usr/bin/env python3
"""Window-parity MCP relay for the sparring exam (exam tooling, not game logic).

The kit's sparring peer alternates roles inside ONE process and dials ONE peer URL; our team is
role-split across two fixed-role processes. This relay terminates MCP and re-calls the current
window's owner: odd windows -> the cop process, even -> the thief process. Ownership updates on
every inbound greeting's sub_game_number. Pure transport routing — no game state.
"""

from __future__ import annotations

import argparse
import sys
import time

from cosmos77_cop.net.client import PeerCallError, PeerClient
from cosmos77_cop.net.server import PeerInbox, build_server
from cosmos77_cop.orchestrator.runtime import start_server

KIND_TO_TOOL = {
    "negotiate": ("negotiate", "message"),
    "turn": ("receive_turn", "message"),
    "control": ("receive_control", "message"),
    "audit": ("submit_audit", "payload"),
}


def main() -> int:
    """Run the relay until killed."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--odd-url", default="http://127.0.0.1:8801/mcp")
    parser.add_argument("--even-url", default="http://127.0.0.1:8802/mcp")
    args = parser.parse_args()

    inbox = PeerInbox(maxsize=500)
    mcp = build_server(inbox, "cosmos77-relay")
    start_server(mcp, args.port)
    odd = PeerClient(args.odd_url)
    even = PeerClient(args.even_url)
    owner = odd
    print(f"relay: :{args.port} -> odd {args.odd_url} / even {args.even_url}", flush=True)
    while True:
        item = inbox.pull(timeout_s=0.5)
        if item is None:
            continue
        kind, payload = item
        if kind == "negotiate":
            sub = payload.get("sub_game_number")
            if isinstance(sub, int):
                owner = odd if sub % 2 == 1 else even
        tool, arg = KIND_TO_TOOL[kind]
        try:
            owner.call(tool, {arg: payload}, deadline_s=10.0)
        except PeerCallError as exc:
            print(f"relay: drop {kind} ({exc})", flush=True)
            time.sleep(0.1)


if __name__ == "__main__":
    sys.exit(main())
