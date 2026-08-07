"""``cosmos-cop`` command-line entry point.

Full subcommands (serve | selfplay | friendly | counted | replay | report | doctor | compare |
kill) land in Phase 7. ``smoke-peer`` is the Phase-5 two-process gate runtime driven by
``make smoke``.
"""

from __future__ import annotations

import argparse
import sys

from cosmos77_cop import __version__

_SUBCOMMANDS = "serve|selfplay|friendly|counted|replay|report|doctor|compare|kill"


def _smoke_peer(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cosmos-cop smoke-peer")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--peer-url", required=True)
    parser.add_argument("--role", choices=["police", "thief"], required=True)
    parser.add_argument("--config", default="config/game.json")
    args = parser.parse_args(argv)
    from cosmos77_cop.orchestrator.smoke import run_smoke_peer

    return run_smoke_peer(
        role=args.role, port=args.port, peer_url=args.peer_url, game_config_path=args.config
    )


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in {"--version", "version"}:
        print(f"cosmos-cop {__version__}")
        return 0
    if args and args[0] == "smoke-peer":
        return _smoke_peer(args[1:])
    if args:
        print(f"cosmos-cop: unknown subcommand {args[0]!r} ({_SUBCOMMANDS} land in Phase 7)")
        return 2
    print(f"cosmos-cop {__version__} — subcommands ({_SUBCOMMANDS}) land in Phase 7")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
