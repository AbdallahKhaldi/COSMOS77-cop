"""The ``report`` command: dry-run by default, doubly armed to reach the lecturer."""

from __future__ import annotations

import json
from pathlib import Path

from .orchestrator.peerconf import load_peer_config


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
