#!/usr/bin/env python3
"""Two-process smoke gate: this repo's peer vs the sibling repo's, over real localhost HTTP.

Spawns both CLIs as SEPARATE processes (playbook §0.1 — never an in-process import of the other
role), waits for both to complete a handshake + one committed turn, exits 0 only on double green.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = REPO.parent
COP = WORKSPACE / "COSMOS77-cop"
THIEF = WORKSPACE / "COSMOS77-thief"
COP_PORT, THIEF_PORT = 8801, 8802


def spawn(repo: Path, tool: str, port: int, peer_port: int, role: str) -> subprocess.Popen:
    """Launch one peer process in its own repo (its own venv — scrub inherited env)."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    cmd = [
        "uv", "run", tool, "smoke-peer",
        "--port", str(port),
        "--peer-url", f"http://127.0.0.1:{peer_port}/mcp",
        "--role", role,
    ]
    return subprocess.Popen(
        cmd, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )


def main() -> int:
    """Run the gate; print both peers' outputs on failure."""
    if not THIEF.is_dir() or not COP.is_dir():
        print("smoke: both COSMOS77-cop and COSMOS77-thief must sit side by side")
        return 2
    cop = spawn(COP, "cosmos-cop", COP_PORT, THIEF_PORT, "police")
    thief = spawn(THIEF, "cosmos-thief", THIEF_PORT, COP_PORT, "thief")
    try:
        cop_rc = cop.wait(timeout=120)
        thief_rc = thief.wait(timeout=120)
    except subprocess.TimeoutExpired:
        cop.kill()
        thief.kill()
        print("smoke: TIMEOUT — a peer hung")
        return 1
    for name, proc in (("cop", cop), ("thief", thief)):
        out = proc.stdout.read().decode() if proc.stdout else ""
        print(f"--- {name} ---\n{out.strip()}")
    if cop_rc == 0 and thief_rc == 0:
        print("smoke: PASS — handshake + one committed turn each way")
        return 0
    print(f"smoke: FAIL (cop={cop_rc}, thief={thief_rc})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
