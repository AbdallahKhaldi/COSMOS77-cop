"""Seeded tie-breaking among EQUALLY-VALUED choices (demo variety, default off).

Deterministic play replays the identical game every run — correct for tests and
reproducibility, lifeless for the public demo.  When ``COSMOS_VARY_SEED`` is
set, choices that are *exact ties* under the strategy's own value function are
resolved by a seeded RNG instead of board-position order, so every run is a
genuinely different real game while strategy strength is untouched (ties are
equal by definition).  Unseeded, every call site preserves its legacy pick
byte-for-byte.  This RNG guards gameplay aesthetics only — nonces and crypto
use ``secrets`` everywhere (playbook §0.2) and never this module.
"""

from __future__ import annotations

import os
import random
from collections.abc import Callable, Iterable

_rng: random.Random | None = None


def arm_from_env() -> None:
    """Read ``COSMOS_VARY_SEED`` once at process start; absent = legacy play."""
    global _rng
    value = os.environ.get("COSMOS_VARY_SEED")
    _rng = random.Random(int(value)) if value else None


def armed() -> bool:
    """True when tie-break variety is active for this process."""
    return _rng is not None


def pick_max[T](items: Iterable[T], key: Callable[[T], object],
                legacy: Callable[[T], object]) -> T:
    """Max by *key*; seeded-random among exact key-ties; legacy order unseeded."""
    pool = list(items)
    if _rng is None:
        return max(pool, key=legacy)  # type: ignore[type-var,arg-type]
    best = max(key(item) for item in pool)  # type: ignore[type-var]
    ties = [item for item in pool if key(item) == best]
    return ties[0] if len(ties) == 1 else _rng.choice(ties)


def pick_min[T](items: Iterable[T], key: Callable[[T], object],
                legacy: Callable[[T], object]) -> T:
    """Min by *key*; seeded-random among exact key-ties; legacy order unseeded."""
    pool = list(items)
    if _rng is None:
        return min(pool, key=legacy)  # type: ignore[type-var,arg-type]
    best = min(key(item) for item in pool)  # type: ignore[type-var]
    ties = [item for item in pool if key(item) == best]
    return ties[0] if len(ties) == 1 else _rng.choice(ties)
