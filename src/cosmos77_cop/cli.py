"""``cosmos-cop`` command-line entry point (playbook §3 CLI surface).

Live: serve | selfplay | kill | compare | doctor | smoke-peer. Landing later: friendly/counted
(Phase 10 arming), replay (Phase 9), report (Phase 10).
"""

from __future__ import annotations

import sys

from cosmos77_cop import __version__

from . import cli_args

_PENDING = "friendly|counted"




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
    }
    if args and args[0] in handlers:
        return handlers[args[0]](args[1:])
    if args and args[0] == "kill":
        from cosmos77_cop.commands import kill_cmd

        return kill_cmd()
    if args and args[0] == "doctor":
        from cosmos77_cop.commands import doctor_cmd

        return doctor_cmd()
    if args:
        print(f"cosmos-cop: unknown subcommand {args[0]!r} ({_PENDING} land in later phases)")
        return 2
    live = "serve|selfplay|console|replay|report|kill|compare|doctor"
    print(f"cosmos-cop {__version__} — {live}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
