"""Play commands: ``serve`` (one series in our fixed role) and ``selfplay`` (two processes)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .crypto.step0 import hardware_spec
from .engine.config import load_game_config
from .orchestrator.brainbridge import ROLE
from .orchestrator.identity import GROUP_ID, TEAM_REPOS
from .orchestrator.peerconf import load_peer_config
from .orchestrator.runtime import start_server
from .orchestrator.series import SeriesDriver
from .protocol.ids import game_id, game_uid
from .protocol.outcome import ZEROED
from .protocol.terms import terms_from_config
from .repoinfo import code_version
from .report.artifacts import ArtifactWriter
from .report.finish import finish_series


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
    gui: bool = False,
    snapshots: str | None = None,
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
    attachment = None
    if gui or snapshots:
        from .gui.attach import ViewAttachment
        from .gui.live import LiveWindow

        window = LiveWindow(f"cosmos77 {ROLE} — local truth") if gui else None
        if window is not None:
            window.open(cfg.grid_size)
        attachment = ViewAttachment(window=window, snapshot_dir=snapshots)
    driver = SeriesDriver(
        game_cfg=cfg,
        peer_cfg=peer,
        gid_a=gid_a,
        gid_b=gid_b,
        out_dir=out,
        code_version=code_version(),
        hardware=hardware_spec(),
        writer=writer,
        alternate_labels=alternate_labels,
        scent_model=scent_model,
        view_attachment=attachment,
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
    zeroed = [r.sub_game_number for r in driver.reports if r.result in ZEROED]
    print(f"series settled={summary['settled']} artifacts in {out}")
    if zeroed:
        # Kit exit-code convention: a settled TECHNICAL-LOSS row is reportable, but it is not a
        # played game — a gate must never read green because six windows all died cleanly.
        print(f"series had zeroed windows: {zeroed}")
        return 6
    return 0 if summary["settled"] else 6
