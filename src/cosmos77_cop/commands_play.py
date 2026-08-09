"""Play commands: ``serve`` (one series in our fixed role) and ``selfplay`` (two processes)."""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

from .arming import ArmingError, declared_count, first_meeting, serve_posture
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
from .strategy import jitter


def seed_github(gid_a: str, gid_b: str, *, selfplay: bool) -> dict[str, dict[str, str]]:
    """``links.github`` seed: OUR repos under our gid(s) only — the peer's arrive via greeting.

    Claiming our URLs for the opponent's gid is a false rule-49 field; in selfplay both
    labels are this team, so both may carry our repos.
    """
    return {g: dict(TEAM_REPOS) for g in (gid_a, gid_b) if selfplay or g == GROUP_ID}


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
    vary_seed: int | None = None,
    counted: bool = False,
    events: bool = False,
) -> int:
    """Play this repo's fixed role through *windows* sub-games and write our artifact set.

    Counted is doubly armed and PRIVATE: ``config/peer.toml [league] counted`` AND
    ``--counted`` together, or the run refuses to start (the shared constitution never
    carries it). ``--events`` appends one JSON line per view to ``<out>/events.jsonl``.
    """
    if vary_seed is not None:
        os.environ["COSMOS_VARY_SEED"] = str(vary_seed)
    jitter.arm_from_env()
    cfg = load_game_config(config_path)
    raw = json.loads(Path(config_path).read_text(encoding="utf-8"))
    peer = dataclasses.replace(
        load_peer_config("config/peer.toml"), my_port=port, opponent_url=peer_url
    )
    our_gid = GROUP_ID if GROUP_ID in (gid_a, gid_b) else gid_a
    opp_gid = gid_b if our_gid == gid_a else gid_a
    try:
        posture = serve_posture(
            config_counted=peer.league_counted, cli_counted=counted, opponent=opp_gid
        )
    except ArmingError as exc:
        print(f"serve: REFUSED — {exc} (peer.toml [league] counted AND serve --counted)")
        return 2
    gid = game_id(gid_a, gid_b)
    uid = game_uid(terms_from_config(raw), gid_a, gid_b)
    writer = ArtifactWriter(
        out,
        gid=gid,
        uid=uid,
        github=seed_github(gid_a, gid_b, selfplay=alternate_labels),
        counted=posture.counted,
        reason=posture.label,
    )
    attachment = None
    if gui or snapshots or events:
        from .gui.attach import ViewAttachment
        from .gui.live import LiveWindow
        from .gui.stream import EventSink

        window = LiveWindow(f"cosmos77 {ROLE} — local truth") if gui else None
        if window is not None:
            window.open(cfg.grid_size)
        sink = EventSink(out) if events else None
        attachment = ViewAttachment(window=window, snapshot_dir=snapshots, extra=sink)
    driver = SeriesDriver(
        game_cfg=cfg,
        peer_cfg=peer,
        gid_a=gid_a,
        gid_b=gid_b,
        out_dir=out,
        code_version=code_version(),
        num_games_declared=declared_count(),
        first_meeting=first_meeting(opp_gid),
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
            summary = finish_series(
                driver,
                writer,
                raw_cfg=raw,
                my_gid=our_gid,
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
