"""``selfplay``: a practice series against the sibling repo, as two real processes.

Never an in-process import of the other role — that would put both agents in one process and
break the separation the league is built on.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .commands_play import serve_cmd
from .orchestrator.brainbridge import ROLE
from .orchestrator.identity import GROUP_ID
from .repoinfo import SIBLING_REPO, SIBLING_TOOL


def selfplay_cmd(
    *, out: str | None = None, windows: int = 6, snapshots: str | None = None,
    scent_model: str | None = None, gui: bool = False, events: bool = False,
    vary_seed: int | None = None,
) -> int:
    """Two-process practice series vs the sibling repo (playbook §0.1 — never in-process)."""
    sibling = Path("..") / SIBLING_REPO
    if not sibling.is_dir():
        print("selfplay: sibling repo not found beside this one (use --dumb once implemented)")
        return 2
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = out or f"runs/selfplay-{stamp}"
    gid_a, gid_b = GROUP_ID, f"{GROUP_ID}-mirror"
    my_port, their_port = (8801, 8802) if ROLE == "police" else (8802, 8801)
    tool = SIBLING_TOOL
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    if vary_seed is not None:
        env["COSMOS_VARY_SEED"] = str(vary_seed + 1)  # sibling varies independently
    peer_proc = subprocess.Popen(
        [
            "uv", "run", tool, "serve",
            "--port", str(their_port),
            "--host", "127.0.0.1",
            "--peer-url", f"http://127.0.0.1:{my_port}/mcp",
            "--gid-a", gid_a, "--gid-b", gid_b,
            "--windows", str(windows),
            "--alternate-labels",
            *(["--scent-model", scent_model] if scent_model else []),
            *(["--gui"] if gui else []),
            *(["--events"] if events else []),
            "--out", f"runs/selfplay-{stamp}",
        ],
        cwd=sibling,
        env=env,
    )
    try:
        rc = serve_cmd(
            vary_seed=vary_seed,
            port=my_port,
            host="127.0.0.1",
            peer_url=f"http://127.0.0.1:{their_port}/mcp",
            gid_a=gid_a,
            gid_b=gid_b,
            windows=windows,
            out=out_dir,
            alternate_labels=True,
            gui=gui,
            snapshots=snapshots,
            scent_model=scent_model,
            events=events,
        )
    finally:
        peer_rc = peer_proc.wait(timeout=120)
    print(f"selfplay: ours rc={rc}, sibling rc={peer_rc}")
    return rc if rc != 0 else (0 if peer_rc == 0 else 6)


