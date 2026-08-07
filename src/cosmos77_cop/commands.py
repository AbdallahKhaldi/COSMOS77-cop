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
from .protocol.outcome import ZEROED
from .protocol.terms import terms_from_config
from .report.artifacts import ArtifactWriter
from .report.compare import compare_files
from .report.finish import finish_series

# The sibling is derived from OUR OWN directory name, never from ROLE: the two repos are kept in
# sync by a token swap, and a `ROLE == "police"` branch inverts under that swap — which silently
# made selfplay spawn a second peer of our own role in our own directory (refused handshake, and
# a series of technical losses). Deriving it this way is stable in both directions.
OUR_REPO = Path(__file__).resolve().parents[2].name
SIBLING_REPO = "COSMOS77-thief" if OUR_REPO == "COSMOS77-cop" else "COSMOS77-cop"
SIBLING_TOOL = "cosmos-" + SIBLING_REPO.rsplit("-", 1)[-1]


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
        code_version=_code_version(),
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


def selfplay_cmd(
    *, out: str | None = None, windows: int = 6, snapshots: str | None = None,
    scent_model: str | None = None,
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
    peer_proc = subprocess.Popen(
        [
            "uv", "run", tool, "serve",
            "--port", str(their_port),
            "--peer-url", f"http://127.0.0.1:{my_port}/mcp",
            "--gid-a", gid_a, "--gid-b", gid_b,
            "--windows", str(windows),
            "--alternate-labels",
            *(["--scent-model", scent_model] if scent_model else []),
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
            snapshots=snapshots,
            scent_model=scent_model,
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


def report_cmd(
    result_path: str,
    *,
    counted: bool = False,
    dry_run: bool = True,
    root: str = ".",
) -> int:
    """Send (or dry-run) the one report a settled series owes. Arming needs BOTH switches."""
    from .report.gatekeeper import ALLOW, Gatekeeper
    from .report.gmail import has_credentials
    from .report.mail import build_message, load_result_bytes
    from .report.recipients import ArmingError, Posture, assert_deliverable, recipients_for

    body = json.loads(Path(result_path).read_text(encoding="utf-8"))
    canonical, filename = load_result_bytes(result_path)
    config_counted = bool((body.get("league") or {}).get("counted"))
    posture = Posture(config_counted=config_counted, cli_counted=counted)
    settled = bool((body.get("mutual_agreement") or {}).get("sha256"))
    try:
        assert_deliverable(
            posture, has_credentials=has_credentials(root) or dry_run, settled=settled
        )
    except ArmingError as exc:
        print(f"report: REFUSED — {exc}")
        return 2
    targets = recipients_for(posture)
    peer = load_peer_config("config/peer.toml")
    keeper = Gatekeeper.from_config(30, peer.mail_burst_capacity, peer.mail_daily_cap)
    message = build_message(
        sender="me",
        recipients=targets,
        game_id=str(body.get("game_id", "unknown")),
        canonical=canonical,
        filename=filename,
    )
    print(f"report: posture={posture.label} recipients={', '.join(targets)}")
    print(f"report: subject={message['Subject']}")
    print(f"report: body == attachment == {len(canonical)} canonical bytes (verified)")
    if dry_run:
        print(f"report: DRY RUN — gatekeeper says {keeper.check(0.0)}; nothing was sent")
        return 0
    from .report.gmail import build_service, send_report

    response = send_report(
        service=build_service(root),
        gatekeeper=keeper,
        sender="me",
        recipients=targets,
        game_id=str(body.get("game_id", "unknown")),
        canonical=canonical,
        filename=filename,
        max_retries=peer.mail_max_retries,
        backoff_base=peer.mail_backoff_base_s,
    )
    print(f"report: sent id={response.get('id')} (gatekeeper {ALLOW})")
    return 0
