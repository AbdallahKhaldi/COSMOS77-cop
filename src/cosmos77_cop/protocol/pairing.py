"""Pairing + uid declaration decisions (kit SPEC §7.2-7.3; PROMOTED/PROPOSED truth tables).

Both ride the negotiate message BESIDE ``terms`` (the signed set is closed). Omission and
uncomparable values are silence — a guard that fail-fasts on silence forfeits against the
unmodified reference peer.
"""

from __future__ import annotations

from typing import Any

PLAY = "play"
REFUSE_SUB_GAME = "refuse:sub_game"
REFUSE_ROLE = "refuse:role"
REFUSE_UID = "refuse"

ROLES = ("police", "thief")


def pairing_decision(ours: dict[str, Any], theirs: dict[str, Any]) -> str:
    """Decide play/refuse from the two pairing declarations (sub_game_number + role)."""
    my_sub, their_sub = ours.get("sub_game_number"), theirs.get("sub_game_number")
    if isinstance(my_sub, int) and isinstance(their_sub, int) and my_sub != their_sub:
        return REFUSE_SUB_GAME
    my_role, their_role = ours.get("role"), theirs.get("role")
    if my_role in ROLES and their_role in ROLES and my_role == their_role:
        return REFUSE_ROLE
    return PLAY


def _comparable_uid(value: object) -> bool:
    return isinstance(value, str) and value.count("-") == 4


def uid_decision(ours: object, theirs: object) -> str:
    """Refuse only when both declared comparable uids that differ; anything else plays."""
    if _comparable_uid(ours) and _comparable_uid(theirs) and ours != theirs:
        return REFUSE_UID
    return PLAY
