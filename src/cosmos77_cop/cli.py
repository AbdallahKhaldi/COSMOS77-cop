"""``cosmos-cop`` command-line entry point (playbook §3 CLI surface).

Live: serve | selfplay | pair | console | replay | report | kill | compare | doctor |
smoke-peer. Counted is a doubly-armed POSTURE, not a subcommand: peer.toml [league]
counted=true AND ``serve --counted`` (run side); result league.counted AND
``report --counted`` (mail side).
"""

from __future__ import annotations

import sys

from cosmos77_cop import __version__

from . import cli_args, cli_doctor, cli_pair


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in {"--version", "version"}:
        print(f"cosmos-cop {__version__}")
        return 0
    handlers = {
        "serve": cli_args.serve,
        "selfplay": cli_args.selfplay,
        "smoke-peer": cli_args.smoke_peer,
        "compare": cli_args.compare,
        "replay": cli_args.replay,
        "console": cli_args.console,
        "report": cli_args.report,
        "pair": cli_pair.pair,
        "doctor": cli_doctor.doctor,
    }
    if args and args[0] in handlers:
        return handlers[args[0]](args[1:])
    if args and args[0] == "kill":
        from cosmos77_cop.commands import kill_cmd

        return kill_cmd()
    if args:
        print(f"cosmos-cop: unknown subcommand {args[0]!r}")
        return 2
    live = "serve|selfplay|pair|console|replay|report|kill|compare|doctor"
    print(f"cosmos-cop {__version__} — {live}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
