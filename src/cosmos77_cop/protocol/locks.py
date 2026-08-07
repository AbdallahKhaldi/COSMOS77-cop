"""Locked-model declarations: registered doc hashes + the refusal rule (kit SPEC §7).

Pair choices that cannot ride in the flat signed terms are declared as SHA-256 hashes of pinned
documents. Refuse ONLY when both peers declare the same family and the hashes differ; omission
NEVER refuses, in either direction; an uncomparable value is silence.
"""

from __future__ import annotations

FAMILIES = ("scent_model", "wire_shape", "info_mode", "smell_binding")

REGISTERED: dict[tuple[str, str], str] = {
    ("scent_model", "subtractive_chebyshev_v1"): (
        "81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4"
    ),
    ("scent_model", "multiplicative_book_v1"): (
        "934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9"
    ),
    ("wire_shape", "reference-v3"): (
        "229ae6487a418c3fcb6da9be404de2f2533c288ebc228811bff6dedc4164d6f7"
    ),
    ("info_mode", "belief"): (
        "020947daeeb3f73494af9b04201326791742c7184085456e3517d21981ee1202"
    ),
}

OUR_LOCKS: dict[str, str] = {
    "scent_model": REGISTERED[("scent_model", "subtractive_chebyshev_v1")],
    "wire_shape": REGISTERED[("wire_shape", "reference-v3")],
    "info_mode": REGISTERED[("info_mode", "belief")],
}


def _comparable(value: object) -> bool:
    hexed = isinstance(value, str) and all(c in "0123456789abcdef" for c in str(value))
    return hexed and len(str(value)) == 64


def lock_conflicts(ours: dict[str, object], theirs: dict[str, object]) -> list[str]:
    """Families where BOTH sides declared comparable hashes that differ (the only refusals)."""
    conflicts = []
    for family in FAMILIES:
        mine, peer = ours.get(family), theirs.get(family)
        if _comparable(mine) and _comparable(peer) and mine != peer:
            conflicts.append(family)
    return conflicts
