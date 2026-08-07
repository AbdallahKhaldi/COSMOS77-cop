"""Constitution loader: parses ``config/game.json`` and enforces App. F statuses (rule 12).

FIXED values may never deviate; MINIMUM values may only be raised; the axis convention and move
set are pinned because the engine's geometry implements exactly them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Coord = tuple[int, int]

_FIXED: dict[tuple[str, str], Any] = {
    ("board_and_agents", "num_agents"): 2,
    ("board_and_agents", "axis_origin_corner"): "top-left",
    ("board_and_agents", "axis_start_index"): 0,
    ("pheromones", "pheromone_grid_size"): 5,
    ("pheromones", "pheromone_center_intensity"): 0.9,
    ("pheromones", "pheromone_decay"): 0.1,
    ("scoring", "capture_cop"): 20,
    ("scoring", "capture_thief"): 5,
    ("scoring", "survival_cop"): 5,
    ("scoring", "survival_thief"): 10,
    ("scoring", "tie_score"): 2,
    ("scoring", "technical_loss"): 0,
    ("movement_and_barriers", "move_set"): ["N", "S", "E", "W", "STAY"],
}

_MINIMUM: dict[tuple[str, str], int] = {
    ("board_and_agents", "grid_size"): 7,
    ("movement_and_barriers", "max_barriers"): 14,
    ("movement_and_barriers", "max_moves"): 35,
    ("movement_and_barriers", "survival_threshold"): 35,
}


class ConfigError(ValueError):
    """A constitution value violates its App. F status (FIXED deviation or lowered MINIMUM)."""


@dataclass(frozen=True)
class GameConfig:
    """Validated, immutable view of the shared constitution."""

    raw: dict[str, Any]
    grid_size: int
    thief_start: Coord
    cop_start: Coord
    map_area: str
    hint_max_words: int
    max_barriers: int
    max_moves: int
    survival_threshold: int
    scoring: dict[str, int]
    pheromone_grid_size: int
    pheromone_center_intensity: float
    pheromone_decay: float
    pheromone_min_center_intensity: float
    num_games: int


def _get(raw: dict[str, Any], section: str, key: str) -> object:
    try:
        return raw[section][key]
    except KeyError as exc:
        raise ConfigError(f"constitution missing {section}.{key}") from exc


def _cell(raw: dict[str, Any], key: str) -> Coord:
    cell = _get(raw, "board_and_agents", key)
    size = _get(raw, "board_and_agents", "grid_size")
    ok = (
        isinstance(cell, list)
        and len(cell) == 2
        and all(isinstance(c, int) and 0 <= c < size for c in cell)
    )
    if not ok:
        raise ConfigError(f"{key} {cell!r} is not an on-board [row, col]")
    return (cell[0], cell[1])


def validate(raw: dict[str, Any]) -> None:
    """Raise :class:`ConfigError` on any FIXED deviation or lowered MINIMUM (rule 12)."""
    for (section, key), pinned in _FIXED.items():
        value = _get(raw, section, key)
        if value != pinned:
            raise ConfigError(f"FIXED {section}.{key} must be {pinned!r}, got {value!r}")
    for (section, key), floor in _MINIMUM.items():
        value = _get(raw, section, key)
        if not isinstance(value, int) or value < floor:
            raise ConfigError(f"MINIMUM {section}.{key} only raisable from {floor}, got {value!r}")
    _cell(raw, "thief_start")
    _cell(raw, "cop_start")


def from_dict(raw: dict[str, Any]) -> GameConfig:
    """Validate *raw* and freeze it into a :class:`GameConfig`."""
    validate(raw)
    return GameConfig(
        raw=raw,
        grid_size=_get(raw, "board_and_agents", "grid_size"),
        thief_start=_cell(raw, "thief_start"),
        cop_start=_cell(raw, "cop_start"),
        map_area=_get(raw, "world", "map_area"),
        hint_max_words=_get(raw, "world", "hint_max_words"),
        max_barriers=_get(raw, "movement_and_barriers", "max_barriers"),
        max_moves=_get(raw, "movement_and_barriers", "max_moves"),
        survival_threshold=_get(raw, "movement_and_barriers", "survival_threshold"),
        scoring={k: int(v) for k, v in raw["scoring"].items()},
        pheromone_grid_size=_get(raw, "pheromones", "pheromone_grid_size"),
        pheromone_center_intensity=_get(raw, "pheromones", "pheromone_center_intensity"),
        pheromone_decay=_get(raw, "pheromones", "pheromone_decay"),
        pheromone_min_center_intensity=_get(raw, "pheromones", "pheromone_min_center_intensity"),
        num_games=_get(raw, "network_and_league", "num_games"),
    )


def load_game_config(path: str | Path) -> GameConfig:
    """Load and validate the shared constitution file at *path*."""
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
