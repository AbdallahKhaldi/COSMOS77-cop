"""Turn and audit delivery with at-least-once retries (kit delivery contract §7.1).

The receiver dedupes on the commit, so re-sending is free; a single transient blip
must never become a zeroed window or an unfiled reveal.
"""

from __future__ import annotations

import time
from typing import Any

from ..net.client import PeerCallError
from ..net.server import KIND_AUDIT, KIND_NEGOTIATE, KIND_TURN
from .gateway import Gateway
from .runtime import route_turn


def send_turn(gateway: Gateway, wire: dict[str, Any]) -> bool:
    """Deliver one turn within the turn budget, RETRYING while budget remains.

    The receiver dedupes on the commit, so re-sending is free (at-least-once is the
    kit's named defence); a single transient blip must not become a zeroed window.
    """
    deadline = time.monotonic() + gateway.peer_cfg.turn_timeout_s
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return False
        try:
            gateway.client.call("receive_turn", {"message": wire}, deadline_s=max(1.0, left))
            return True
        except PeerCallError:
            if deadline - time.monotonic() <= 0.5:
                return False
            time.sleep(min(1.0, max(0.1, (deadline - time.monotonic()) / 4)))


def exchange_audits(
    gateway: Gateway, records: list[dict[str, Any]], result_claim: str, timeout_s: float
) -> dict[str, Any] | None:
    """Submit our reveal (retried within the window), then wait for theirs."""
    payload = {"sender": gateway.role, "records": records, "result_claim": result_claim}
    submit_deadline = time.monotonic() + min(timeout_s, 3 * gateway.peer_cfg.turn_timeout_s)
    delivered = False
    while not delivered and time.monotonic() < submit_deadline:
        try:
            gateway.client.call("submit_audit", {"payload": payload},
                                deadline_s=gateway.peer_cfg.turn_timeout_s)
            delivered = True
        except PeerCallError:
            time.sleep(0.5)
    if not delivered:
        return None
    if gateway.pending_audits:
        return gateway.pending_audits.pop(0)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        item = gateway.inbox.pull(timeout_s=gateway.peer_cfg.poll_s)
        if item and item[0] == KIND_AUDIT:
            return item[1]
        if item and item[0] == KIND_TURN:
            gateway.pending_turns.extend(route_turn(gateway, item[1]))
        elif item and item[0] == KIND_NEGOTIATE:
            gateway.pending_greetings.append(item[1])
    return None
