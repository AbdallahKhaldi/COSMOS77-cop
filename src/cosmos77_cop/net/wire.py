"""Turn-message admission per the kit's PROMOTED wire surface (vectors/turn_message.json).

The vector's validation table is the contract two independently-written peers meet on:
required keys refused when missing or mistyped, unknown keys tolerated (the extension
seam), ``timestamp`` decorative but non-empty, ``commit`` exactly 64 lowercase hex.
Refusing here — before the receiver, before the fold — turns a malformed opponent turn
into a counted refusal instead of a mid-fold crash five layers deeper.
"""

from __future__ import annotations

import re

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
SENDERS = ("police", "thief")


def refuse_turn(message: object) -> str | None:
    """The refusal reason for *message*, or ``None`` when it may enter the receiver."""
    if not isinstance(message, dict):
        return "turn message must be an object"
    try:
        step = int(message["step"])
    except (KeyError, TypeError, ValueError):
        return "step: required int"
    if step < 1:
        return "step: required positive int (steps number 1..max_steps)"
    if message.get("sender") not in SENDERS:
        return "sender: required 'police' | 'thief'"
    if not isinstance(message.get("hint"), str):  # may be empty; may be a lie (App. E)
        return "hint: required str"
    grid = message.get("smell_grid")
    if not isinstance(grid, dict):
        return "smell_grid: required object"
    for key, value in grid.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"smell_grid[{key!r}]: required number"
    commit = message.get("commit")
    if not isinstance(commit, str) or not _HEX64.match(commit):
        return "commit: required 64-char lowercase hex"
    stamp = message.get("timestamp")
    if not isinstance(stamp, str) or not stamp:
        return "timestamp: required non-empty str"
    return None  # unknown keys tolerated and ignored — the extension seam
