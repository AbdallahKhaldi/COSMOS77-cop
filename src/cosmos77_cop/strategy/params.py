"""Strategy tunables with their single source of defaults.

Private per-peer values (never negotiated, never signed). ``config/peer.toml`` overlays these
from Phase 5 on; nothing else in the codebase may restate a default.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyParams:
    """Knobs for both brains; defaults are the played configuration until peer.toml overrides."""

    claim_threshold: float = 0.9
    reserve_barriers: int = 2
    taboo_distance: int = 1
    escape_horizon: int = 3
    place_range: int = 3


def from_overlay(overlay: Mapping[str, Any]) -> StrategyParams:
    """The defaults with ``peer.toml [strategy]`` applied on top.

    A key this dataclass does not define is REFUSED rather than dropped: a knob that
    is silently ignored makes the config file describe a run that never happened, and
    the operator would tune a number that cannot move.  Failing here costs a restart;
    failing silently costs a game played on settings nobody chose.
    """
    known = {field.name for field in dataclasses.fields(StrategyParams)}
    unknown = sorted(set(overlay) - known)
    if unknown:
        raise ValueError(
            f"peer.toml [strategy]: unknown key(s) {', '.join(unknown)}; "
            f"known keys are {', '.join(sorted(known))}"
        )
    return dataclasses.replace(StrategyParams(), **dict(overlay))
