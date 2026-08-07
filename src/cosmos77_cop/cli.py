"""``cosmos-cop`` command-line entry point (playbook §3 CLI surface).

Live: serve | selfplay | kill | compare | doctor | smoke-peer. Landing later: friendly/counted
(Phase 10 arming), replay (Phase 9), report (Phase 10).
"""

from __future__ import annotations

import argparse
import sys

from cosmos77_cop import __version__

_PENDING = "friendly|counted"


def _serve(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cosmos-cop serve")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--peer-url", required=True)
    parser.add_argument("--gid-a", required=True)
    parser.add_argument("--gid-b", required=True)
    parser.add_argument("--windows", type=int, default=6)
    parser.add_argument("--windows-spec", default=None, help="comma subset, e.g. 1,3,5")
    parser.add_argument("--no-close", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--snapshots", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--config", default="config/game.json")
    parser.add_argument("--alternate-labels", action="store_true")
    parser.add_argument(
        "--scent-model",
        default=None,
        choices=["subtractive_chebyshev_v1", "multiplicative_book_v1"],
    )
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import serve_cmd

    return serve_cmd(
        port=args.port,
        peer_url=args.peer_url,
        gid_a=args.gid_a,
        gid_b=args.gid_b,
        windows=args.windows,
        out=args.out,
        config_path=args.config,
        alternate_labels=args.alternate_labels,
        scent_model=args.scent_model,
        windows_spec=args.windows_spec,
        close=not args.no_close,
        gui=args.gui,
        snapshots=args.snapshots,
    )


def _selfplay(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cosmos-cop selfplay")
    parser.add_argument("--out", default=None)
    parser.add_argument("--windows", type=int, default=6)
    parser.add_argument("--snapshots", default=None)
    parser.add_argument(
        "--scent-model",
        default=None,
        choices=["subtractive_chebyshev_v1", "multiplicative_book_v1"],
    )
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import selfplay_cmd

    return selfplay_cmd(
        out=args.out, windows=args.windows, snapshots=args.snapshots,
        scent_model=args.scent_model,
    )


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


def _replay(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cosmos-cop replay")
    parser.add_argument("log")
    parser.add_argument("--screenshot", default=None, help="directory for SVG stamps")
    parser.add_argument("--expect-clean", action="store_true")
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import replay_cmd

    return replay_cmd(args.log, screenshot_dir=args.screenshot, expect_clean=args.expect_clean)


def _report(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cosmos-cop report")
    parser.add_argument("result")
    parser.add_argument("--counted", action="store_true", help="second arming switch (rule 37)")
    parser.add_argument("--send", action="store_true", help="actually send; default is a dry run")
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import report_cmd

    return report_cmd(args.result, counted=args.counted, dry_run=not args.send)


def _compare(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cosmos-cop compare")
    parser.add_argument("ours")
    parser.add_argument("theirs")
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import compare_cmd

    return compare_cmd(args.ours, args.theirs)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in {"--version", "version"}:
        print(f"cosmos-cop {__version__}")
        return 0
    handlers = {
        "serve": _serve,
        "selfplay": _selfplay,
        "smoke-peer": _smoke_peer,
        "compare": _compare,
        "replay": _replay,
        "report": _report,
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
    print(f"cosmos-cop {__version__} — serve|selfplay|replay|report|kill|compare|doctor|smoke-peer")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
