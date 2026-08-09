"""``doctor`` argument parsing: bare = local health check, flags = opponent probe."""

from __future__ import annotations

import argparse

DEFAULT_PUBLIC_BASE = "https://cosmos77-arena-production.up.railway.app"


def doctor(argv: list[str]) -> int:
    """Dispatch ``doctor``: no arguments keeps the local health check; flags run the probe."""
    if not argv:
        from cosmos77_cop.commands import doctor_cmd

        return doctor_cmd()
    parser = argparse.ArgumentParser(prog="cosmos-cop doctor", add_help=True)
    parser.add_argument("--json", action="store_true", help="machine-readable report (implied)")
    parser.add_argument("--url", default=None, help="single endpoint serving BOTH roles")
    parser.add_argument("--cop-url", default=None, help="their cop endpoint (per-role shape)")
    parser.add_argument("--thief-url", default=None, help="their thief endpoint (per-role shape)")
    parser.add_argument("--their-config", default=None, help="their game config JSON to diff")
    parser.add_argument("--gid", default=None, help="their group id (enables uid derivation)")
    parser.add_argument(
        "--their-greeting", default=None,
        help="a captured negotiate message JSON for offline lock/forensics analysis",
    )
    parser.add_argument("--public-base", default=DEFAULT_PUBLIC_BASE,
                        help="our public base URL (topology stage prints what they dial)")
    parser.add_argument("--config", default="config/game.json")
    args = parser.parse_args(argv)
    per_role = bool(args.cop_url or args.thief_url)
    if args.url and per_role:
        print("doctor: give --url OR --cop-url/--thief-url, not both")
        return 2
    if per_role and not (args.cop_url and args.thief_url):
        print("doctor: per-role shape needs BOTH --cop-url and --thief-url")
        return 2
    if not (args.url or per_role or args.their_config or args.their_greeting):
        print("doctor: nothing to probe — give --url, --cop-url/--thief-url, "
              "--their-config or --their-greeting")
        return 2
    from cosmos77_cop.commands_doctor import doctor_probe_cmd

    return doctor_probe_cmd(
        url=args.url, cop_url=args.cop_url, thief_url=args.thief_url,
        their_config=args.their_config, their_gid=args.gid,
        their_greeting=args.their_greeting, public_base=args.public_base,
        config_path=args.config,
    )
