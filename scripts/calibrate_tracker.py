#!/usr/bin/env python3
"""Tracker calibration: our per-step argmax vs the opponent's audit-revealed position trail.

Under ``subtractive_chebyshev_v1`` the offset MUST be 0 — the transmitted grid's argmax is the
emitter's current cell. A non-zero offset means the peer emits at a different point in its turn
than we assume, and the per-opponent offset must be stored before any counted run (playbook §4.7).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def calibrate(log_path: Path) -> tuple[int, int, dict[int, int]]:
    """Return (matches, comparable, offset_histogram) for one log file."""
    log = json.loads(log_path.read_text(encoding="utf-8"))
    trace = (log.get("summary") or {}).get("tracker_trace") or []
    revealed = [
        (int(r["payload"]["step"]), r["payload"]["position"])
        for r in log.get("opponent_records", [])
        if isinstance(r.get("payload"), dict) and "position" in r["payload"]
    ]
    revealed.sort()
    matches = comparable = 0
    histogram: dict[int, int] = {}
    for index, estimate in enumerate(trace):
        if estimate is None or index >= len(revealed):
            continue
        comparable += 1
        for offset in (0, -1, 1):
            target = index + offset
            if 0 <= target < len(revealed) and list(revealed[target][1]) == list(estimate):
                histogram[offset] = histogram.get(offset, 0) + 1
                if offset == 0:
                    matches += 1
                break
    return matches, comparable, histogram


def main() -> int:
    """Calibrate every log in a run directory; non-zero exit on any offset drift."""
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()
    total_match = total_cmp = 0
    combined: dict[int, int] = {}
    for log_path in sorted(Path(args.run_dir).glob("log_*.json")):
        matches, comparable, histogram = calibrate(log_path)
        total_match += matches
        total_cmp += comparable
        for offset, count in histogram.items():
            combined[offset] = combined.get(offset, 0) + count
        print(f"{log_path.name}: {matches}/{comparable} at offset 0  {histogram}")
    print(f"\nTOTAL {total_match}/{total_cmp} exact at offset 0; histogram {combined}")
    if not total_cmp:
        print("NO EXACT ESTIMATES: expected under a non-transmitting scent model (belief mode)")
        return 0
    if total_match == total_cmp:
        print("CALIBRATION CLEAN: offset 0, inversion is exact")
        return 0
    print("CALIBRATION DRIFT: store the per-opponent offset before any counted run")
    return 1


if __name__ == "__main__":
    sys.exit(main())
