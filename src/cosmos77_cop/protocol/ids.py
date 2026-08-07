"""Deterministic match ids both peers derive with no round-trip (kit SPEC §4).

Both constructions SORT the group pair, so neither side must be told which name to use. The uid
input is the flat 14-key terms — declared in the greeting so a wrong derivation dies at handshake
(SPAR-N10), not at report-diff.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from .canonical import canonical_str


def game_id(group_a: str, group_b: str) -> str:
    """``"-vs-".join(sorted(pair))`` — names all four artifact files."""
    return "-vs-".join(sorted([group_a, group_b]))


def game_uid(terms: dict[str, Any], group_a: str, group_b: str) -> str:
    """UUID from the first 16 digest bytes of ``SHA256(canonical(terms)|gid1|gid2)`` (sorted)."""
    pair = sorted([group_a, group_b])
    seed = f"{canonical_str(terms)}|{'|'.join(pair)}"
    return str(uuid.UUID(bytes=hashlib.sha256(seed.encode()).digest()[:16]))


def artifact_filenames(gid: str, sub_game: int | None = None) -> dict[str, str]:
    """App. F table-20 filename grammar; per-sub-game files carry a zero-padded ``_g<NN>``."""
    suffix = f"_g{sub_game:02d}" if sub_game is not None else "_g<NN>"
    return {
        "declaration": f"declaration_{gid}.json",
        "config": f"config_{gid}{suffix}.json",
        "log": f"log_{gid}{suffix}.json",
        "result": f"result_{gid}.json",
    }
