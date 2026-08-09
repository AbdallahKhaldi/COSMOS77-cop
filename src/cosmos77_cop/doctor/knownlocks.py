"""Identify an opponent's locked-model hashes against every form the kit pins.

``KNOWN_LOCKS`` maps ``sha256 -> {kind, name}`` for the registered docs in
``protocol/locks.REGISTERED`` plus the divergent forms the community kit pins in
``vectors/locked_model.json`` (bookletter-v3 wire, ``exact`` info mode, both smell bindings).
Verdicts follow the kit's refusal rule: matching green, known-but-different yellow (with the
auto-adapt note when we support their variant), unknown red, omission never refuses.
"""

from __future__ import annotations

from typing import Any

from ..protocol.locks import FAMILIES, OUR_LOCKS, REGISTERED
from .report import GREEN, RED, YELLOW, Stage, worst

KNOWN_LOCKS: dict[str, dict[str, str]] = {
    REGISTERED[("scent_model", "subtractive_chebyshev_v1")]: {
        "kind": "scent_model", "name": "subtractive_chebyshev_v1"
    },
    REGISTERED[("scent_model", "multiplicative_book_v1")]: {
        "kind": "scent_model", "name": "multiplicative_book_v1 (book figure-4 grid kernel)"
    },
    REGISTERED[("wire_shape", "reference-v3")]: {"kind": "wire_shape", "name": "reference-v3"},
    "f3fc1d424c461a02a1db9490306318c46043501bc1da1bfcb1b56ff9bc76f376": {
        "kind": "wire_shape", "name": "bookletter-v3 (kit-pinned divergent form, PROPOSED)"
    },
    REGISTERED[("info_mode", "belief")]: {"kind": "info_mode", "name": "belief"},
    "be93ca76794f1bf638572f532bba32e08131737397febf377395abe7333c5489": {
        "kind": "info_mode", "name": "exact"
    },
    "f471af61ad178939e528b1346f996ed52f46fb06c9f420d913bf26dec524c5a6": {
        "kind": "smell_binding", "name": "none (unbound default)"
    },
    "7992141d219704e56a10d0c263c0272755760d0556d3271eeff3950bb366309b": {
        "kind": "smell_binding", "name": "commit_grid_v1"
    },
}

_ADAPT = {
    "scent_model": "we auto-adapt: run our side with `serve --scent-model {token}` "
    "(we support both registered scent models)"
}


def extract_locks(greeting: dict[str, Any]) -> dict[str, str]:
    """The ``<family>_sha256`` declarations found anywhere in a greeting-shaped mapping."""
    found: dict[str, str] = {}
    for family in FAMILIES:
        value = greeting.get(f"{family}_sha256")
        if isinstance(value, str) and value:
            found[family] = value
    return found


def _verdict(family: str, theirs: str) -> tuple[str, str, str | None]:
    """(status, line, fix) for one declared hash against ours."""
    known = KNOWN_LOCKS.get(theirs)
    ours = OUR_LOCKS.get(family)
    if known is None:
        return (
            RED,
            f"{family}: UNKNOWN hash {theirs[:16]}… — not any form the kit pins",
            f"send us the {family} doc behind {theirs[:16]}… (family/name/params/example, "
            "kit locked_model schema) so we can compare models",
        )
    if ours is None:
        return (GREEN, f"{family}: {known['name']} — we are silent; omission never refuses", None)
    if ours == theirs:
        return (GREEN, f"{family}: {known['name']} — matches ours", None)
    line = f"{family}: {known['name']} — known but DIFFERENT from ours"
    if family in _ADAPT:
        token = known["name"].split(" ")[0]
        return (YELLOW, line, _ADAPT[family].format(token=token))
    return (YELLOW, line, f"agree one {family} — we play {_our_name(family)} only")


def _our_name(family: str) -> str:
    """The registered name of OUR declared hash for *family*."""
    entry = KNOWN_LOCKS.get(OUR_LOCKS.get(family, ""), {})
    return entry.get("name", "our registered form")


def locks_stage(observed: dict[str, Any] | None) -> Stage:
    """Stage 3: identify each of their lock hashes, or note that none were observed."""
    if not observed or not extract_locks(observed):
        return Stage(
            "locks",
            GREEN,
            "no lock hashes observed (legal — omission never refuses; the reference wire "
            "returns only ok:true, so pass a captured greeting via --their-greeting to compare)",
            detail={"ours": dict(OUR_LOCKS)},
        )
    theirs = extract_locks(observed)
    rows = [(family, *_verdict(family, digest)) for family, digest in sorted(theirs.items())]
    fixes = [fix for _, _, _, fix in rows if fix]
    return Stage(
        "locks",
        worst([status for _, status, _, _ in rows]),
        "; ".join(line for _, _, line, _ in rows),
        fix_line="; ".join(fixes) if fixes else None,
        detail={"ours": dict(OUR_LOCKS), "theirs": theirs},
    )
