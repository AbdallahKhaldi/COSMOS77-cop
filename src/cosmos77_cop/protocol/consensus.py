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

    Rows are trimmed to the reference's FIVE-key form — sub_game_number, roles, result,
    winner_group, score.  ``tie`` stays in the document row but is NOT signed: the reference's
    emit.py deliberately leaves it out of the hash preimage, and every hash ever settled live
    reproduces only under the five-key row (kit SPEC §6 correction of 2026-08-13; the kit itself
    documented a six-key row from 08-04 to 08-13, which this module was first built against — a
    signer that keeps ``tie`` fails settlement against every played implementation, and on a
    counted series that is rule 35, zero for BOTH teams).  Nothing is lost: tie is derivable as
    ``winner_group == null`` and the tie COUNT sits in the signed aggregate.  Timestamps and
    token counts are per-side and stay out.
    """
    keep = ("sub_game_number", "roles", "result", "winner_group", "score")
    trimmed = [{k: row[k] for k in keep if k in row} for row in sub_games]
    return {"game_id": gid, "aggregate": aggregate, "sub_games": trimmed}
