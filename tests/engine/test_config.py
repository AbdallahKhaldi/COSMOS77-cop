"""Constitution loader: App. F statuses enforced (rule 12), repo default loads clean."""

import copy
import json
from pathlib import Path

import pytest

from cosmos77_cop.engine.config import ConfigError, from_dict, load_game_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_raw() -> dict:
    return json.loads((REPO_ROOT / "config" / "game.json").read_text(encoding="utf-8"))


def test_repo_constitution_loads_and_freezes():
    cfg = load_game_config(REPO_ROOT / "config" / "game.json")
    assert cfg.grid_size == 7
    assert cfg.thief_start == (3, 3)
    assert cfg.cop_start == (0, 0)
    assert cfg.max_barriers == 14
    assert cfg.max_moves == 35
    assert cfg.survival_threshold == 35
    assert cfg.num_games == 6
    assert cfg.pheromone_center_intensity == 0.9
    assert cfg.map_area == "New York"


@pytest.mark.parametrize(
    ("section", "key", "bad"),
    [
        ("board_and_agents", "num_agents", 3),
        ("pheromones", "pheromone_grid_size", 7),
        ("pheromones", "pheromone_center_intensity", 0.8),
        ("pheromones", "pheromone_decay", 0.2),
        ("scoring", "capture_cop", 25),
        ("scoring", "survival_thief", 12),
        ("scoring", "tie_score", 3),
        ("scoring", "technical_loss", 1),
        ("board_and_agents", "axis_origin_corner", "bottom-left"),
        ("board_and_agents", "axis_start_index", 1),
        ("movement_and_barriers", "move_set", ["N", "S", "E", "W"]),
    ],
)
def test_fixed_values_refuse_any_deviation(section, key, bad):
    raw = repo_raw()
    raw[section][key] = bad
    with pytest.raises(ConfigError, match="FIXED"):
        from_dict(raw)


@pytest.mark.parametrize(
    ("section", "key", "lowered"),
    [
        ("board_and_agents", "grid_size", 6),
        ("movement_and_barriers", "max_barriers", 13),
        ("movement_and_barriers", "max_moves", 34),
        ("movement_and_barriers", "survival_threshold", 34),
    ],
)
def test_minimums_refuse_lowering(section, key, lowered):
    raw = repo_raw()
    raw[section][key] = lowered
    with pytest.raises(ConfigError, match="MINIMUM"):
        from_dict(raw)


def test_minimums_accept_raising():
    raw = repo_raw()
    raw["board_and_agents"]["grid_size"] = 9
    raw["movement_and_barriers"]["max_barriers"] = 16
    cfg = from_dict(raw)
    assert cfg.grid_size == 9
    assert cfg.max_barriers == 16


def test_missing_key_and_off_board_start_refused():
    raw = repo_raw()
    del raw["world"]["hint_max_words"]
    with pytest.raises(ConfigError, match="missing"):
        from_dict(raw)
    raw2 = copy.deepcopy(repo_raw())
    raw2["board_and_agents"]["thief_start"] = [7, 3]
    with pytest.raises(ConfigError, match="on-board"):
        from_dict(raw2)
