#!/usr/bin/env python3
"""The Phase-8 sparring exam: a full alternating six-window series vs the kit peer.

Topology: sparring (one process, roles alternate) dials our window-parity relay; our cop repo
plays the odd windows, our thief repo the even ones, sequenced through the SHARED artifact
directory; the thief-side driver (owning window 6) closes and writes the result.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WS = REPO.parent
KIT = WS / "kit"


def spawn(cmd: list[str], cwd: Path, log: Path) -> subprocess.Popen:
    """Launch one process with its own log file."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    handle = log.open("w")
    return subprocess.Popen(cmd, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT)


def main() -> int:
    """Run one exam series; exit 0 only when our side settles 6/6."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="exam")
    parser.add_argument("--spar-role", default="thief", choices=["thief", "police"])
    parser.add_argument("--policy", default="greedy", choices=["greedy", "random"])
    parser.add_argument("--scent-model", default="subtractive_chebyshev_v1")
    parser.add_argument("--hint-lang", default="mixed")
    parser.add_argument("--turn-timeout", default="180")
    parser.add_argument("--seed", default="42")
    args = parser.parse_args()

    stamp = time.strftime("%H%M%S")
    out = (REPO / "runs" / f"sparring-{args.label}-{stamp}").resolve()
    out.mkdir(parents=True)
    logs = out / "_process_logs"
    logs.mkdir()

    odd_role_is_cop = args.spar_role == "thief"
    cop_windows, thief_windows = ("1,3,5", "2,4,6") if odd_role_is_cop else ("2,4,6", "1,3,5")
    closer_is_thief = "6" in thief_windows

    common = [
        "--gid-a", "cosmos77", "--gid-b", "sparring-local",
        "--windows", "6", "--out", str(out), "--config", "config/game.sparring.json",
    ]
    if args.scent_model != "subtractive_chebyshev_v1":
        common += ["--scent-model", args.scent_model]
    cop = spawn(
        ["uv", "run", "cosmos-cop", "serve", "--port", "8801",
         "--peer-url", "http://127.0.0.1:8931/mcp", "--windows-spec", cop_windows]
        + common + ([] if not closer_is_thief else ["--no-close"]),
        REPO, logs / "cop.log",
    )
    thief = spawn(
        ["uv", "run", "cosmos-thief", "serve", "--port", "8802",
         "--peer-url", "http://127.0.0.1:8931/mcp", "--windows-spec", thief_windows]
        + common + (["--no-close"] if not closer_is_thief else []),
        WS / "COSMOS77-thief", logs / "thief.log",
    )
    odd_url = "http://127.0.0.1:8801/mcp" if "1" in cop_windows else "http://127.0.0.1:8802/mcp"
    even_url = "http://127.0.0.1:8802/mcp" if "1" in cop_windows else "http://127.0.0.1:8801/mcp"
    relay = spawn(
        ["uv", "run", "python", "scripts/sparring_relay.py", "--port", "8800",
         "--odd-url", odd_url, "--even-url", even_url],
        REPO, logs / "relay.log",
    )
    time.sleep(4)
    sparring = spawn(
        [str(KIT / ".venv" / "bin" / "python"), "-m", "sparring.cli", "serve",
         "--port", "8931", "--peer", "http://127.0.0.1:8800/mcp",
         "--role", args.spar_role, "--policy", args.policy,
         "--scent-model", args.scent_model, "--hint-lang", args.hint_lang,
         "--turn-timeout", args.turn_timeout, "--seed", args.seed,
         "--artifacts", str(out / "sparring-side")],
        KIT, logs / "sparring.log",
    )
    try:
        cop_rc = cop.wait(timeout=900)
        thief_rc = thief.wait(timeout=900)
        spar_rc = sparring.wait(timeout=120)
    except subprocess.TimeoutExpired:
        for proc in (cop, thief, sparring):
            proc.kill()
        print("exam: TIMEOUT")
        return 1
    finally:
        relay.kill()
    print(f"exam[{args.label}]: cop rc={cop_rc} thief rc={thief_rc} sparring rc={spar_rc}")
    print(f"artifacts: {out}")
    for name in ("cop", "thief", "sparring"):
        text = (logs / f"{name}.log").read_text()
        tail = [ln for ln in text.splitlines() if ln.strip()][-6:]
        print(f"--- {name} ---")
        print("\n".join(tail))
    return 0 if (cop_rc == 0 and thief_rc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
