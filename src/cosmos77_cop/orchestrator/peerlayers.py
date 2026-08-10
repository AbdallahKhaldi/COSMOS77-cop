"""The two layers wrapped around ``peer.toml``: the deployed ENVIRONMENT and the SIGNED terms.

Precedence, tightest last: dataclass default < environment variable < ``config/peer.toml`` <
``config/game.json``.

The environment layer exists because ``peer.toml`` is gitignored (it names our ports and the
opponent's URLs), so the hub image — which clones both agent repos from GitHub — does not have
it. Without this layer every private knob would silently fall back to its dataclass default in
production: ``trash_provider`` would read ``template`` on the machine that actually plays, and
the graded Gemini deliverable would be dead exactly where it is graded.

The signed layer exists because a term BOTH teams agreed must beat a private preference: the
negotiated ``response_timeout_sec``/``watchdog_timeout_sec`` are what the opponent is entitled to
rely on, so a local ``turn_timeout_seconds`` may never quietly outlive them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..engine.config import GAME_CONFIG

__all__ = ["ENV_KEYS", "GAME_CONFIG", "SIGNED_KEYS", "apply_env", "apply_signed"]

#: ``peer.toml`` (section, key) -> the environment variable that fills it when absent.
ENV_KEYS: dict[tuple[str, str], str] = {
    ("trash_talk", "provider"): "COSMOS_TRASH_PROVIDER",
    ("trash_talk", "model"): "COSMOS_TRASH_MODEL",
    ("league", "counted"): "COSMOS_LEAGUE_COUNTED",
}

#: ``peer.toml`` (section, key) -> the SIGNED ``game.json`` (block, key) that overrides it.
SIGNED_KEYS: dict[tuple[str, str], tuple[str, str]] = {
    ("network", "turn_timeout_seconds"): ("network_and_league", "response_timeout_sec"),
    ("network", "watchdog_seconds"): ("network_and_league", "watchdog_timeout_sec"),
    ("network", "queue_depth"): ("rate_limiter_gatekeeper", "queue_depth"),
}

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _coerce(text: str) -> bool | str:
    """A TOML-shaped value from an environment string; only booleans need decoding."""
    lowered = text.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    return text


def _sections(raw: dict[str, Any]) -> dict[str, Any]:
    """A shallow copy whose table values are safe to write into."""
    return {k: dict(v) if isinstance(v, dict) else v for k, v in raw.items()}


def apply_env(raw: dict[str, Any], environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Fill only the keys ABSENT from *raw* from the environment — the file always wins."""
    env = os.environ if environ is None else environ
    merged = _sections(raw)
    for (section, key), variable in ENV_KEYS.items():
        text = env.get(variable, "")
        if text and key not in (merged.get(section) or {}):
            merged.setdefault(section, {})[key] = _coerce(text)
    return merged


def apply_signed(raw: dict[str, Any], path: str | Path = GAME_CONFIG) -> dict[str, Any]:
    """Overlay the signed constitution onto every parallel private key — it always wins.

    An absent constitution overlays nothing: the private defaults are then all we have, and a
    run with no ``game.json`` has no negotiated term to honour in the first place.
    """
    target = Path(path)
    if not target.exists():
        return _sections(raw)
    signed = json.loads(target.read_text(encoding="utf-8"))
    merged = _sections(raw)
    for (section, key), (block, signed_key) in SIGNED_KEYS.items():
        value = (signed.get(block) or {}).get(signed_key)
        if value is not None:
            merged.setdefault(section, {})[key] = value
    return merged
