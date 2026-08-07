"""The flat 14 signed terms and the pre-game agreement signature (kit SPEC §4; rule 11).

The key set is CLOSED — adding a key breaks the signature. The uid derives from exactly this
extraction, never from the whole config (the classic silent cross-team failure).
"""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_str

TERMS_KEYS: tuple[str, ...] = (
    "board_size",
    "smell_grid_size",
    "decay_per_step",
    "emit_intensity",
    "min_center_intensity",
    "max_steps",
    "barriers_max",
    "setting",
    "hint_max_words",
    "axis_origin_corner",
    "axis_start_index",
    "thief_start",
    "cop_start",
    "num_games",
)

_CONFIG_PATHS: dict[str, tuple[str, str]] = {
    "board_size": ("board_and_agents", "grid_size"),
    "smell_grid_size": ("pheromones", "pheromone_grid_size"),
    "decay_per_step": ("pheromones", "pheromone_decay"),
    "emit_intensity": ("pheromones", "pheromone_center_intensity"),
    "min_center_intensity": ("pheromones", "pheromone_min_center_intensity"),
    "max_steps": ("movement_and_barriers", "max_moves"),
    "barriers_max": ("movement_and_barriers", "max_barriers"),
    "setting": ("world", "map_area"),
    "hint_max_words": ("world", "hint_max_words"),
    "axis_origin_corner": ("board_and_agents", "axis_origin_corner"),
    "axis_start_index": ("board_and_agents", "axis_start_index"),
    "thief_start": ("board_and_agents", "thief_start"),
    "cop_start": ("board_and_agents", "cop_start"),
    "num_games": ("network_and_league", "num_games"),
}


def terms_from_config(raw: dict[str, Any]) -> dict[str, Any]:
    """EXTRACT the flat signed terms from a full ``game.json`` structure (never hash the whole)."""
    return {key: raw[section][field] for key, (section, field) in _CONFIG_PATHS.items()}


def validate_terms(terms: dict[str, Any]) -> list[str]:
    """Return the keys missing from *terms* against the closed 14-key set (empty = complete)."""
    return [k for k in TERMS_KEYS if k not in terms]


def terms_signature(terms: dict[str, Any], nonce: str) -> str:
    """``SHA256(canonical_json(terms)|nonce)`` — the same construction as a step commit."""
    return hashlib.sha256(f"{canonical_str(terms)}|{nonce}".encode()).hexdigest()
