"""``pair``: print the console pairing packet as JSON on stdout (the hub shells this).

Zero new derivation logic — it reuses :func:`cosmos77_cop.console.pairing.build_packet`, so the
JSON a hub renders is exactly the derivation the console page shows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def pair(argv: list[str]) -> int:
    """Parse ``pair`` arguments and print the pairing packet as one JSON object."""
    parser = argparse.ArgumentParser(prog="cosmos-cop pair")
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--their-cop", required=True)
    parser.add_argument("--their-thief", required=True)
    parser.add_argument("--our-cop", default="(our cop MCP URL)")
    parser.add_argument("--our-thief", default="(our thief MCP URL)")
    parser.add_argument("--config", default="config/game.json")
    args = parser.parse_args(argv)
    from cosmos77_cop.console.pairing import build_packet

    raw = json.loads(Path(args.config).read_text(encoding="utf-8"))
    packet = build_packet(
        raw,
        opponent=args.opponent,
        our_cop=args.our_cop,
        our_thief=args.our_thief,
        their_cop=args.their_cop,
        their_thief=args.their_thief,
    )
    print(json.dumps(packet.as_dict(), sort_keys=True))
    return 0
