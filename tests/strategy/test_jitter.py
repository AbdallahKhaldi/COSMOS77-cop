"""Tie-break variety: seeded games differ, unseeded play is byte-identical legacy."""

from __future__ import annotations

import pytest

from cosmos77_cop.engine.board import Board
from cosmos77_cop.strategy import jitter, solver


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COSMOS_VARY_SEED", raising=False)
    jitter.arm_from_env()
    solver.clear_cache()


def test_unseeded_picks_are_exact_legacy_order() -> None:
    """No env seed → pick_min/pick_max reduce to plain min/max on the legacy key."""
    items = [(2, "b"), (1, "d"), (1, "a"), (3, "c")]
    assert jitter.pick_min(items, key=lambda x: x[0], legacy=lambda x: x) == (1, "a")
    assert jitter.pick_max(items, key=lambda x: x[0], legacy=lambda x: x) == (3, "c")
    assert not jitter.armed()


def test_seeded_pick_stays_inside_the_exact_tie_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Variety never trades value: only exact key-ties are eligible."""
    monkeypatch.setenv("COSMOS_VARY_SEED", "7")
    jitter.arm_from_env()
    items = [(1, "a"), (1, "b"), (1, "c"), (2, "z")]
    for _ in range(20):
        cost, _label = jitter.pick_min(items, key=lambda x: x[0], legacy=lambda x: x)
        assert cost == 1


def test_two_seeds_diverge_on_a_tie_rich_board(monkeypatch: pytest.MonkeyPatch) -> None:
    """Different seeds walk different (equally optimal) thief paths on the bare board."""

    def path(seed: int) -> list[tuple[int, int]]:
        monkeypatch.setenv("COSMOS_VARY_SEED", str(seed))
        jitter.arm_from_env()
        solver.clear_cache()
        board = Board(7)
        cop, thief = (0, 0), (3, 3)
        cells = []
        for _ in range(8):
            thief, _r = solver.best_thief_move(board, cop, thief)
            cells.append(thief)
        return cells

    walks = {tuple(path(seed)) for seed in (1, 2, 3, 4, 5)}
    assert len(walks) > 1, "seeded runs must not all replay the identical path"


def test_same_seed_replays_the_same_game(monkeypatch: pytest.MonkeyPatch) -> None:
    """A given seed is reproducible — variety, not chaos."""

    def path(seed: int) -> list[tuple[int, int]]:
        monkeypatch.setenv("COSMOS_VARY_SEED", str(seed))
        jitter.arm_from_env()
        solver.clear_cache()
        board = Board(7)
        cop, thief = (0, 0), (3, 3)
        cells = []
        for _ in range(6):
            thief, _r = solver.best_thief_move(board, cop, thief)
            cells.append(thief)
        return cells

    assert path(42) == path(42)
