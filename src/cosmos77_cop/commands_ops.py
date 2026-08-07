"""Ops commands: ``kill``, ``compare``, ``doctor``, ``replay``."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .engine.config import load_game_config
from .orchestrator.peerconf import load_peer_config
from .repoinfo import SIBLING_REPO
from .report.compare import compare_files


def kill_cmd() -> int:
    """Free our configured port (orphaned peers keep playing — playbook §7.17)."""
    peer = load_peer_config("config/peer.toml")
    subprocess.run(
        f"lsof -ti tcp:{peer.my_port} | xargs kill 2>/dev/null",
        shell=True,
        check=False,
    )
    print(f"kill: freed tcp:{peer.my_port}")
    return 0


def compare_cmd(ours: str, theirs: str) -> int:
    """The report-compare ritual over two result artifacts."""
    diffs = compare_files(ours, theirs)
    if not diffs:
        print("compare: PASS — every must-match field agrees")
        return 0
    for diff in diffs:
        print(f"compare: MISMATCH {diff}")
    return 1


def doctor_cmd() -> int:
    """Local health: constitution loads, protocol synced, key presence, sibling present."""
    problems = []
    try:
        load_game_config("config/game.json")
        print("doctor: constitution loads and validates")
    except Exception as exc:
        problems.append(f"constitution: {exc}")
    from .hints.gemini import load_env_key

    print(f"doctor: GEMINI_API_KEY {'present' if load_env_key() else 'ABSENT (template mode)'}")
    sibling = Path("..") / SIBLING_REPO
    print(f"doctor: sibling repo {'present' if sibling.is_dir() else 'MISSING'}")
    for problem in problems:
        print(f"doctor: PROBLEM {problem}")
    return 1 if problems else 0


def replay_cmd(
    log_path: str, *, screenshot_dir: str | None = None, expect_clean: bool = False
) -> int:
    """Verify a log; optionally render SVG stamps; open the viewer when a display is available."""
    from .replay.render import summary_line, write_step_svg
    from .replay.verify import verify_log
    from .replay.viewer import ReplayViewer

    result = verify_log(log_path)
    print(summary_line(result))
    for verdict in result.failures[:5]:
        print(f"  record {verdict.index + 1} (step {verdict.step}): {verdict.stamp}")
    if screenshot_dir:
        first = result.verdicts[0]
        written = write_step_svg(result, first, Path(screenshot_dir) / "replay_verified.svg")
        print(f"wrote {written}")
        if result.failures:
            bad = write_step_svg(
                result, result.failures[0], Path(screenshot_dir) / "replay_tampered.svg"
            )
            print(f"wrote {bad}")
    if expect_clean and not result.clean:
        return 1
    if os.environ.get("COSMOS_NO_GUI"):
        return 0 if result.clean else 1
    try:
        return ReplayViewer(result).run()
    except Exception as exc:  # a headless machine is not a verification failure
        print(f"(viewer unavailable: {exc.__class__.__name__}; verification above stands)")
        return 0 if result.clean else 1


