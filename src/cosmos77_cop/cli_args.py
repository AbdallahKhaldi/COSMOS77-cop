"""Argument parsers for each ``cosmos-cop`` subcommand (kept out of the dispatch file)."""

from __future__ import annotations

import argparse


def serve(argv: list[str]) -> int:
    """Parse ``serve`` arguments and play one series in this repo's fixed role."""
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
    parser.add_argument(
        "--counted", action="store_true",
        help="run-side arming half; peer.toml [league] counted=true is the other half",
    )
    parser.add_argument(
        "--events", action="store_true", help="append per-turn JSONL to <out>/events.jsonl"
    )
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
        counted=args.counted,
        events=args.events,
    )


def selfplay(argv: list[str]) -> int:
    """Parse ``selfplay`` arguments and run a two-process practice series."""
    parser = argparse.ArgumentParser(prog="cosmos-cop selfplay")
    parser.add_argument("--out", default=None)
    parser.add_argument("--windows", type=int, default=6)
    parser.add_argument("--snapshots", default=None)
    parser.add_argument("--gui", action="store_true", help="open the live window on both sides")
    parser.add_argument(
        "--events", action="store_true", help="per-turn JSONL in both processes' run dirs"
    )
    parser.add_argument(
        "--scent-model",
        default=None,
        choices=["subtractive_chebyshev_v1", "multiplicative_book_v1"],
    )
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import selfplay_cmd

    return selfplay_cmd(
        out=args.out, windows=args.windows, snapshots=args.snapshots,
        scent_model=args.scent_model, gui=args.gui, events=args.events,
    )


def smoke_peer(argv: list[str]) -> int:
    """Parse ``smoke-peer`` arguments and run the Phase-5 two-process gate."""
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


def replay(argv: list[str]) -> int:
    """Parse ``replay`` arguments and verify a sealed log."""
    parser = argparse.ArgumentParser(prog="cosmos-cop replay")
    parser.add_argument("log")
    parser.add_argument("--screenshot", default=None, help="directory for SVG stamps")
    parser.add_argument("--expect-clean", action="store_true")
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import replay_cmd

    return replay_cmd(args.log, screenshot_dir=args.screenshot, expect_clean=args.expect_clean)


def report(argv: list[str]) -> int:
    """Parse ``report`` arguments and dry-run (or send) the series report."""
    parser = argparse.ArgumentParser(prog="cosmos-cop report")
    parser.add_argument("result")
    parser.add_argument("--counted", action="store_true", help="second arming switch (rule 37)")
    parser.add_argument("--send", action="store_true", help="actually send; default is a dry run")
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import report_cmd

    return report_cmd(args.result, counted=args.counted, dry_run=not args.send)


def console(argv: list[str]) -> int:
    """Parse ``console`` arguments and serve the local ops panel."""
    parser = argparse.ArgumentParser(prog="cosmos-cop console")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    from cosmos77_cop.console.server import run_console

    return run_console(".", port=args.port, open_browser=not args.no_browser)


def compare(argv: list[str]) -> int:
    """Parse ``compare`` arguments and run the report-compare ritual."""
    parser = argparse.ArgumentParser(prog="cosmos-cop compare")
    parser.add_argument("ours")
    parser.add_argument("theirs")
    args = parser.parse_args(argv)
    from cosmos77_cop.commands import compare_cmd

    return compare_cmd(args.ours, args.theirs)


