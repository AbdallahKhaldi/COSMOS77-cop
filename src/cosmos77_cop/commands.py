"""CLI command implementations behind ``cosmos-cop`` (serve, selfplay, kill, compare, doctor)."""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import time
from pathlib import Path

from .crypto.step0 import current_commit, hardware_spec
from .engine.config import load_game_config
from .orchestrator.brainbridge import ROLE
from .orchestrator.identity import GROUP_ID, TEAM_REPOS
from .orchestrator.peerconf import load_peer_config
from .orchestrator.runtime import start_server
from .orchestrator.series import SeriesDriver
from .protocol.ids import game_id, game_uid
from .protocol.terms import terms_from_config
from .report.artifacts import ArtifactWriter
from .report.compare import compare_files
from .report.finish import finish_series


def _code_version() -> str:
    try:
        return current_commit(".")
    except Exception:
        return "unknown"


def serve_cmd(
    *,
    port: int,
    peer_url: str,
    gid_a: str,
    gid_b: str,
    windows: int,
    out: str,
    config_path: str = "config/game.json",
    alternate_labels: bool = False,
    scent_model: str | None = None,
    windows_spec: str | None = None,
    close: bool = True,
) -> int:
    """Play this repo's fixed role through *windows* sub-games and write our artifact set."""
    cfg = load_game_config(config_path)
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    peer = dataclasses.replace(
        load_peer_config("config/peer.toml"), my_port=port, opponent_url=peer_url
    )
    gid = game_id(gid_a, gid_b)
    uid = game_uid(terms_from_config(raw), gid_a, gid_b)
    writer = ArtifactWriter(
        out,
        gid=gid,
        uid=uid,
        github={gid_a: dict(TEAM_REPOS), gid_b: dict(TEAM_REPOS)},
        counted=False,
        reason="friendly",
    )
    driver = SeriesDriver(
        game_cfg=cfg,
        peer_cfg=peer,
        gid_a=gid_a,
        gid_b=gid_b,
        out_dir=out,
        code_version=_code_version(),
        hardware=hardware_spec(),
        writer=writer,
        alternate_labels=alternate_labels,
        scent_model=scent_model,
    )
    todo = (
        [int(w) for w in windows_spec.split(",")] if windows_spec else list(range(1, windows + 1))
    )
    server = start_server(driver.mcp, port)
    summary = {"settled": False}
    try:
        for window in todo:
            report = driver.play_window(window)
            settled = bool(report.settlement and report.settlement.settled)
            print(f"g{window:02d} {ROLE}: {report.result} ({report.reason}) settled={settled}")
        if close:
            my_gid = GROUP_ID if GROUP_ID in (gid_a, gid_b) else gid_a
            summary = finish_series(
                driver,
                writer,
                raw_cfg=raw,
                my_gid=my_gid,
                my_identity=driver.gateway_for(todo[0]).identity,
                peer_identity=driver.peer_identity,
                expected_windows=windows,
            )
        else:
            summary = {"settled": all(
                r.settlement is not None and r.settlement.settled for r in driver.reports
            )}
    finally:
        server.should_exit = True
        driver.client.close()
    print(f"series settled={summary['settled']} artifacts in {out}")
    return 0 if summary["settled"] else 6


def selfplay_cmd(*, out: str | None = None, windows: int = 6) -> int:
    """Two-process practice series vs the sibling repo (playbook §0.1 — never in-process)."""
    sibling = Path("..") / ("COSMOS77-thief" if ROLE == "police" else "COSMOS77-cop")
    if not sibling.is_dir():
        print("selfplay: sibling repo not found beside this one (use --dumb once implemented)")
        return 2
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = out or f"runs/selfplay-{stamp}"
    gid_a, gid_b = GROUP_ID, f"{GROUP_ID}-mirror"
    my_port, their_port = (8801, 8802) if ROLE == "police" else (8802, 8801)
    tool = "cosmos-thief" if ROLE == "police" else "cosmos-cop"
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    peer_proc = subprocess.Popen(
        [
            "uv", "run", tool, "serve",
            "--port", str(their_port),
            "--peer-url", f"http://127.0.0.1:{my_port}/mcp",
            "--gid-a", gid_a, "--gid-b", gid_b,
            "--windows", str(windows),
            "--alternate-labels",
            "--out", f"runs/selfplay-{stamp}",
        ],
        cwd=sibling,
        env=env,
    )
    try:
        rc = serve_cmd(
            port=my_port,
            peer_url=f"http://127.0.0.1:{their_port}/mcp",
            gid_a=gid_a,
            gid_b=gid_b,
            windows=windows,
            out=out_dir,
            alternate_labels=True,
        )
    finally:
        peer_rc = peer_proc.wait(timeout=120)
    print(f"selfplay: ours rc={rc}, sibling rc={peer_rc}")
    return rc if rc != 0 else (0 if peer_rc == 0 else 6)


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
    sibling = Path("..") / ("COSMOS77-thief" if ROLE == "police" else "COSMOS77-cop")
    print(f"doctor: sibling repo {'present' if sibling.is_dir() else 'MISSING'}")
    for problem in problems:
        print(f"doctor: PROBLEM {problem}")
    return 1 if problems else 0
