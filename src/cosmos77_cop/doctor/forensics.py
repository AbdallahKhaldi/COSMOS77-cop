"""Signature forensics: name WHICH serialization dialect produced an observed hash.

When a signature or commit mismatches (the SPAR-N04 pattern), recompute it under every published
construction — the reference compact canonical, the book-ch.5 spaced-separator serialization, the
nonce-inside-the-JSON listing form, and the nonce|move audit-snippet form pinned by the kit's
``vectors/commit_reveal.json`` divergent_forms — and tell the opponent exactly what to change.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..protocol.canonical import canonical_str
from ..protocol.consensus import spaced_str
from .report import GREEN, RED, YELLOW, Stage, skipped

REFERENCE = "reference_compact"


def _sha(preimage: str) -> str:
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def _preimages(payload: dict[str, Any], nonce: str) -> list[tuple[str, str, str]]:
    """(dialect, preimage, fix_line) for every known construction, reference first."""
    forms = [
        (
            REFERENCE,
            f"{canonical_str(payload)}|{nonce}",
            "no change — this is the reference dialect",
        ),
        (
            "book_ch5_spaced",
            f"{spaced_str(payload)}|{nonce}",
            "your serializer uses spaced separators (book ch.5 form) — switch to compact "
            "separators (',',':')",
        ),
        (
            "ascii_escaped",
            f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}|{nonce}",
            "your serializer escapes non-ASCII to \\uXXXX — serialize with ensure_ascii=False",
        ),
        (
            "nonce_inside_compact",
            canonical_str({**payload, "nonce": nonce}),
            "your hash puts the nonce INSIDE the JSON (book ch.5 listing form) — pipe-append it "
            "outside: sha256(canonical(payload) + '|' + nonce)",
        ),
    ]
    move = payload.get("move")
    if isinstance(move, str):
        forms.append(
            (
                "nonce_move_only",
                f"{nonce}|{move}",
                "your hash consumes only nonce|move (book audit-snippet form) — hash the FULL "
                "canonical record with the nonce pipe-appended",
            )
        )
    return forms


def identify_dialect(
    payload: dict[str, Any], nonce: str, observed: str
) -> tuple[str, str] | None:
    """The (dialect, fix_line) whose hash equals *observed*, or ``None`` when nothing matches."""
    for name, preimage, fix in _preimages(payload, nonce):
        if _sha(preimage) == observed:
            return name, fix
    return None


def forensics_stage(sample: dict[str, Any] | None) -> Stage:
    """Stage 6: given ``{payload|terms, nonce, signature}``, name the dialect their bytes match."""
    if not sample:
        return skipped("forensics", "no signature sample (no N04 observed, no --their-greeting)")
    payload = sample.get("payload") or sample.get("terms")
    nonce, observed = sample.get("nonce"), sample.get("signature") or sample.get("commit")
    if not isinstance(payload, dict) or not nonce or not observed:
        return skipped("forensics", "sample lacks a payload/nonce/signature triple")
    match = identify_dialect(payload, str(nonce), str(observed))
    if match and match[0] == REFERENCE:
        return Stage(
            "forensics",
            GREEN,
            "signature verifies under the reference dialect (compact canonical JSON, "
            "nonce pipe-appended outside)",
        )
    if match:
        name, fix = match
        return Stage(
            "forensics",
            YELLOW,
            f"their bytes match the {name} dialect, not the reference construction",
            fix_line=fix,
            detail={"matched_dialect": name},
        )
    expected = {name: _sha(pre) for name, pre, _ in _preimages(payload, str(nonce))}
    return Stage(
        "forensics",
        RED,
        "signature matches NO known dialect — raw compare below; ask for their exact "
        "preimage string bytes",
        fix_line="print the exact string you hash (before sha256) and diff it against "
        f"ours: {canonical_str(payload)}|{nonce}",
        detail={"observed": str(observed), "expected_per_dialect": expected},
    )
