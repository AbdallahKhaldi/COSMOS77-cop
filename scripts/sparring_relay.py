#!/usr/bin/env python3
"""Window-parity MCP relay for single-URL opponents (exam tooling, not game logic).

The kit's sparring peer alternates roles inside ONE process and dials ONE peer URL; our team is
role-split across two fixed-role processes. This relay terminates MCP and re-calls the current
window's owner. The league rule is "first-sorted group polices the ODD sub-games", so which of
our processes owns the odd windows depends on the gid sort: pass ``--gid-a/--gid-b`` and the
parity is derived (an opponent sorting before us puts our COP on the EVEN windows). Without
gids the historical default (cop on odds) applies. Ownership updates on every inbound
greeting's ``sub_game_number``. Pure transport routing — no game state.
"""

from __future__ import annotations

import argparse
import sys
import time

from cosmos77_cop.net.client import PeerCallError, PeerClient
from cosmos77_cop.net.server import PeerInbox, build_server
from cosmos77_cop.orchestrator.identity import GROUP_ID
from cosmos77_cop.orchestrator.runtime import start_server

KIND_TO_TOOL = {
    "negotiate": ("negotiate", "message"),
    "turn": ("receive_turn", "message"),
    "control": ("receive_control", "message"),
    "audit": ("submit_audit", "payload"),
}


def cop_owns_odds(gid_a: str | None, gid_b: str | None, ours: str = GROUP_ID) -> bool:
    """Whether OUR cop process owns the odd windows: true iff our gid sorts first.

    Hardcoding odd->cop mis-routes every opponent whose gid sorts before ours (ASCII
    sort: uppercase gids sort before "cosmos77"). No gids -> the historical default.
    """
    if not gid_a or not gid_b:
        return True
    mine = ours if ours in (gid_a, gid_b) else gid_a
    return mine == sorted([gid_a, gid_b])[0]


def main() -> int:
    """Run the relay until killed."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--odd-url", default="http://127.0.0.1:8801/mcp",
                        help="the COP process (owns odd windows when our gid sorts first)")
    parser.add_argument("--even-url", default="http://127.0.0.1:8802/mcp",
                        help="the THIEF process")
    parser.add_argument("--gid-a", default=None, help="one gid of the pairing (parity derivation)")
    parser.add_argument("--gid-b", default=None, help="the other gid of the pairing")
    args = parser.parse_args()

    inbox = PeerInbox(maxsize=500)
    mcp = build_server(inbox, "cosmos77-relay")
    start_server(mcp, args.port)
    cop = PeerClient(args.odd_url)
    thief = PeerClient(args.even_url)
    on_odds = cop_owns_odds(args.gid_a, args.gid_b)
    owner = cop if on_odds else thief
    print(
        f"relay: :{args.port} -> cop {args.odd_url} / thief {args.even_url} "
        f"(cop owns {'odd' if on_odds else 'even'} windows)",
        flush=True,
    )
    while True:
        item = inbox.pull(timeout_s=0.5)
        if item is None:
            continue
        kind, payload = item
        if kind == "negotiate":
            sub = payload.get("sub_game_number")
            if isinstance(sub, int):
                owner = cop if (sub % 2 == 1) == on_odds else thief
        tool, arg = KIND_TO_TOOL[kind]
        try:
            owner.call(tool, {arg: payload}, deadline_s=10.0)
        except PeerCallError as exc:
            print(f"relay: drop {kind} ({exc})", flush=True)
            time.sleep(0.1)


if __name__ == "__main__":
    sys.exit(main())
