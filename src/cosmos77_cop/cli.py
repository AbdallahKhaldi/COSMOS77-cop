"""``cosmos-cop`` command-line entry point.

Subcommands (serve | selfplay | friendly | counted | replay | report | doctor | compare | kill)
land in Phase 7; until then the CLI only identifies itself.
"""

from __future__ import annotations

import sys

from cosmos77_cop import __version__

_SUBCOMMANDS = "serve|selfplay|friendly|counted|replay|report|doctor|compare|kill"


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in {"--version", "version"}:
        print(f"cosmos-cop {__version__}")
        return 0
    print(f"cosmos-cop {__version__} — subcommands ({_SUBCOMMANDS}) land in Phase 7")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
