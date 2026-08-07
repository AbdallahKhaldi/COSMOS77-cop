"""Which repo we are, which one is our sibling, and what commit is playing.

The sibling is derived from OUR OWN directory name, never from ROLE: the two repos are kept in
sync by a token swap, and a ``ROLE == "police"`` branch inverts under that swap — which silently
made selfplay spawn a second peer of our own role in our own directory (refused handshake, and a
series of technical losses).
"""

from __future__ import annotations

from pathlib import Path

from .crypto.step0 import current_commit

OUR_REPO = Path(__file__).resolve().parents[2].name
SIBLING_REPO = "COSMOS77-thief" if OUR_REPO == "COSMOS77-cop" else "COSMOS77-cop"
SIBLING_TOOL = "cosmos-" + SIBLING_REPO.rsplit("-", 1)[-1]


def code_version() -> str:
    """The commit being played, or ``"unknown"`` outside a git checkout."""
    try:
        return current_commit(".")
    except Exception:
        return "unknown"
