#!/usr/bin/env python3
"""Warm a sleeping endpoint until it answers 406 — the MCP ready signal (never 200).

A free Render dyno sleeps after ~15 minutes and takes ~50 s to wake, so this runs ~10 minutes
before any window. Exit 0 only when the endpoint is genuinely ready; a warm-up that "finishes"
without proof is how a window gets burned.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable

from cosmos77_cop.net.probes import READY, probe


def warm(
    url: str,
    *,
    budget_s: float,
    interval_s: float,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Poll *url* until it is ready or the budget runs out; returns a process exit code."""
    deadline = clock() + budget_s
    last = "never probed"
    while clock() < deadline:
        status, kind = probe(url)
        last = f"{status} {kind}"
        if kind == READY:
            print(f"warmup: {url} is READY ({status})")
            return 0
        print(f"warmup: {url} -> {last}; retrying")
        sleep(interval_s)
    print(f"warmup: {url} never became ready within {budget_s:.0f}s (last: {last})")
    return 1


def main() -> int:
    """Warm every URL given on the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--budget", type=float, default=180.0)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    codes = [warm(url, budget_s=args.budget, interval_s=args.interval) for url in args.urls]
    return max(codes)


if __name__ == "__main__":
    sys.exit(main())
