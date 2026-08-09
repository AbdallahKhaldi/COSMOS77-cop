"""Uid stage (config diff, uid derivation, wrapper detection) + topology stage.

The uid stage extracts the flat 14 signed terms from an opponent's config file — unwrapping any
wrapper object they nest it under — diffs term-by-term, derives ``game_uid`` under our gid pair
from both extractions, and separates SUBSTANCE differences (red/uid-fatal) from WRAPPER-ONLY
differences (``schema_version``/``_note``/``agreed_between`` placeholders — yellow, pasteable fix).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..protocol.canonical import canonical_hash
from ..protocol.ids import game_uid
from ..protocol.terms import terms_from_config, validate_terms
from .report import GREEN, RED, YELLOW, Stage, skipped

_WRAPPER_KEYS = ("config", "game", "game_config", "constitution", "game_json")
_WRAPPER_TOP = {"schema_version", "agreed_between"}


def unwrap_config(raw: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    """Find the constitution inside *raw*: (terms, how) via extraction, flat terms, or wrappers."""
    try:
        return terms_from_config(raw), "standard sections"
    except (KeyError, TypeError):
        pass
    if isinstance(raw, dict) and not validate_terms(raw):
        return dict(raw), "flat 14-term file"
    for key in _WRAPPER_KEYS:
        inner = raw.get(key) if isinstance(raw, dict) else None
        if isinstance(inner, dict):
            found = unwrap_config(inner)
            if found:
                return found[0], f"nested under '{key}'"
    return None


def _substance(raw: dict[str, Any]) -> dict[str, Any]:
    """The config minus wrapper-only keys (schema_version, agreed_between, _underscored)."""
    return {k: v for k, v in raw.items() if k not in _WRAPPER_TOP and not k.startswith("_")}


def uid_stage(
    path: str | None, their_gid: str | None, *, our_raw: dict[str, Any], our_gid: str
) -> Stage:
    """Stage 5: diff their config against ours term-by-term and derive uid both ways."""
    if path is None:
        return skipped("uid", "no --their-config given")
    try:
        theirs_raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Stage("uid", RED, f"their config is unreadable: {exc}",
                     fix_line="send a parseable JSON config file")
    found = unwrap_config(theirs_raw)
    if found is None:
        return Stage("uid", RED,
                     "could not locate the constitution in their file — none of the standard "
                     "sections, a flat 14-term object, or a known wrapper key matched",
                     fix_line="send the game config with the standard sections "
                     "(board_and_agents/pheromones/movement_and_barriers/world/"
                     "network_and_league) or the flat 14 signed terms")
    their_terms, how = found
    ours = terms_from_config(our_raw)
    gid_b = their_gid or "<their-gid>"
    detail: dict[str, Any] = {
        "extracted_via": how,
        "game_uid_ours": game_uid(ours, our_gid, gid_b),
        "game_uid_theirs": game_uid(their_terms, our_gid, gid_b),
        "config_sha256_ours": canonical_hash(our_raw),
        "config_sha256_theirs": canonical_hash(theirs_raw),
        "gid_pair_assumed": their_gid is None,
    }
    diffs = [f"{k}: ours={ours[k]!r} theirs={their_terms.get(k)!r}"
             for k in ours if their_terms.get(k) != ours[k]]
    if diffs:
        detail["term_diffs"] = diffs
        return Stage("uid", RED,
                     "signed terms differ — signature AND game_uid both diverge: "
                     + "; ".join(diffs),
                     fix_line="align these constitution values with ours: " + "; ".join(diffs),
                     detail=detail)
    fix = _agreed_between_fix(our_gid, their_gid)
    if detail["config_sha256_ours"] == detail["config_sha256_theirs"]:
        return Stage("uid", GREEN,
                     f"configs byte-identical under canonical form ({how}); "
                     f"game_uid {detail['game_uid_ours']} derives identically both sides",
                     detail=detail)
    if _substance(theirs_raw) == _substance(our_raw):
        return Stage("uid", YELLOW,
                     "substance identical, wrapper differs — only schema_version/_note/"
                     "agreed_between-class keys diverge; terms, signature and game_uid all agree",
                     fix_line=fix, detail=detail)
    unsigned = sorted(
        k for k in set(_substance(theirs_raw)) | set(_substance(our_raw))
        if _substance(theirs_raw).get(k) != _substance(our_raw).get(k)
    )
    detail["unsigned_diff_sections"] = unsigned
    return Stage("uid", YELLOW,
                 "the 14 signed terms agree (same uid/signature) but unsigned sections differ: "
                 + ", ".join(unsigned) + " — engines may score or move differently",
                 fix_line="align the unsigned sections too (scoring/movement drive the engine "
                 "even though they are outside the signed terms): " + ", ".join(unsigned),
                 detail=detail)


def _agreed_between_fix(our_gid: str, their_gid: str | None) -> str:
    pair = json.dumps(sorted([our_gid, their_gid or "<your-gid>"]))
    return (f'set "agreed_between": {pair} (sorted) in BOTH copies — wrapper keys sit outside '
            "the 14 signed terms, so this cannot change the signature or the uid")


def topology_stage(*, single: bool | None, public_base: str) -> Stage:
    """Stage 7: name their URL shape and the exact URLs their shape should dial on us."""
    base = public_base.rstrip("/")
    dial_us = {
        "our_cop_endpoint": f"{base}/cop/mcp",
        "our_thief_endpoint": f"{base}/thief/mcp",
        "single_url_opponents_dial": f"{base}/mcp",
    }
    shape = ("unknown (no URL flags given)" if single is None else
             "single-endpoint-both-roles" if single else "per-role endpoints")
    return Stage("topology", GREEN,
                 f"their shape: {shape}; we pair in BOTH directions with either shape — "
                 "we dial any full URL per role, and inbound single-URL opponents use our "
                 "hub relay",
                 detail={"their_shape": shape, "we_can_dial_them": True,
                         "they_can_dial_us": True, "dial_us": dial_us})
