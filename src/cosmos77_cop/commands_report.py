"""The ``report`` command: dry-run by default, doubly armed to reach the lecturer.

A CONFIRMED counted send is the one event that advances the rule-52 ledger — friendlies
and dry runs never touch it (rules 37-38: the ledger is the evidence behind every count
we declare, and a discarded attempt sent no report and wrote no ledger entry).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine.config import signed_value
from .orchestrator.peerconf import load_peer_config

GATEKEEPER = "rate_limiter_gatekeeper"


def _advance_ledger(body: dict[str, Any], root: str) -> int:
    """Advance the rule-52 ledger by the counted send that just succeeded."""
    from .net.messages import now_iso
    from .orchestrator.identity import GROUP_ID
    from .report.ledger import LEDGER_FILE, Ledger, LedgerError

    rows = body.get("sub_games") or []
    opponent = next((str(g) for g in body.get("groups") or [] if g != GROUP_ID), "unknown")
    ledger = Ledger.load(Path(root) / LEDGER_FILE)
    try:
        ledger.record(
            opponent=opponent,
            game_id=str(body.get("game_id", "unknown")),
            game_uid=str(body.get("game_uid", "unknown")),
            won=(body.get("final_result") or {}).get("winner_group") == GROUP_ID,
            settled_at=str(rows[-1].get("ended_at") or now_iso()) if rows else now_iso(),
        )
    except LedgerError as exc:
        print(f"report: LEDGER ERROR — {exc}; reconcile {LEDGER_FILE} by hand before anything else")
        return 1
    print(f"report: rule-52 ledger advanced to {ledger.counted_games_played} — commit it")
    return 0


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
    # ADR-004: the refill rate is the SIGNED requests_per_minute the opponent relies on; only
    # the burst and the daily cap are ours. A literal here made the docstring a lie (§0.14).
    rpm = int(signed_value(GATEKEEPER, "requests_per_minute"))
    keeper = Gatekeeper.from_config(rpm, peer.mail_burst_capacity, peer.mail_daily_cap)
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
    if posture.counted:
        return _advance_ledger(body, root)
    return 0
