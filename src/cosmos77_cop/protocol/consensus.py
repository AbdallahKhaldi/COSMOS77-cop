"""Report consensus signature — the release's ONE spaced-separator construction (SPEC §6).

``json.dumps(report, sort_keys=True, ensure_ascii=False)`` with DEFAULT separators, SHA-256,
computed BEFORE the Hebrew signature key is inserted (sign-then-insert). Verify = pop the key,
re-serialize spaced, re-hash.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CONSENSUS_KEY = "חתימת_קונסנזוס_משותפת"


def spaced_str(obj: object) -> str:
    """The spaced serialization used ONLY by this signature."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def report_consensus_signature(report: dict[str, Any]) -> str:
    """SHA-256 over the spaced form of *report* (which must NOT contain the signature key)."""
    return hashlib.sha256(spaced_str(report).encode("utf-8")).hexdigest()


def sign_report(report: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *report* with the consensus signature inserted under the Hebrew key."""
    body = {k: v for k, v in report.items() if k != CONSENSUS_KEY}
    signed = dict(body)
    signed[CONSENSUS_KEY] = report_consensus_signature(body)
    return signed


def verify_report(signed: dict[str, Any]) -> bool:
    """Pop the signature key, re-serialize spaced, re-hash, compare."""
    if CONSENSUS_KEY not in signed:
        return False
    body = {k: v for k, v in signed.items() if k != CONSENSUS_KEY}
    return report_consensus_signature(body) == signed[CONSENSUS_KEY]


def consensus_scope(
    gid: str, aggregate: dict[str, Any], sub_games: list[dict[str, Any]]
) -> dict[str, Any]:
    """The ``mutual_agreement.sha256`` preimage: everything both teams must agree on, only that.

    Rows are trimmed to sub_game_number, roles, result, winner_group, tie, score — timestamps
    and token counts are per-side and stay out.
    """
    keep = ("sub_game_number", "roles", "result", "winner_group", "tie", "score")
    trimmed = [{k: row[k] for k in keep if k in row} for row in sub_games]
    return {"game_id": gid, "aggregate": aggregate, "sub_games": trimmed}
