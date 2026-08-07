"""Strategy tunables with their single source of defaults.

Private per-peer values (never negotiated, never signed). ``config/peer.toml`` overlays these
from Phase 5 on; nothing else in the codebase may restate a default.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyParams:
    """Knobs for both brains; defaults are the played configuration until peer.toml overrides."""

    claim_threshold: float = 0.9
    reserve_barriers: int = 2
    taboo_distance: int = 1
