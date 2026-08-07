"""Tracker: exact argmax inversion of transmitted grids, degraded fallback, junk tolerance."""

from cosmos77_cop.strategy.tracker import EXACT, FUZZY, Tracker, parse_grid


def synthetic_emission(center, intensity=0.9, falloff=0.3, size=7) -> dict[str, float]:
    grid = {}
    for r in range(size):
        for c in range(size):
            ring = max(abs(r - center[0]), abs(c - center[1]))
            v = round(intensity - falloff * ring, 3)
            if v > 0:
                grid[f"{r},{c}"] = v
    return grid


def test_argmax_recovers_every_emitter_cell():
    t = Tracker()
    for r in range(7):
        for c in range(7):
            t.observe_grid(synthetic_emission((r, c)))
            assert t.estimate() == ((r, c), EXACT)


def test_two_frame_delta_breaks_stale_ties():
    t = Tracker()
    t.observe_grid({"3,3": 0.9, "2,2": 0.5})
    stale = {"3,3": 0.8, "4,3": 0.9, "2,2": 0.4}
    t.observe_grid(stale)
    assert t.estimate() == ((4, 3), EXACT)


def test_empty_grid_degrades_but_keeps_last_cell():
    t = Tracker()
    t.observe_grid(synthetic_emission((5, 1)))
    t.observe_grid({})
    cell, confidence = t.estimate()
    assert confidence == FUZZY
    assert cell == (5, 1)


def test_parse_ignores_malformed_keys():
    parsed = parse_grid({"3,4": 0.9, "junk": 1.0, "1,2,3": 0.5, "a,b": 0.2, "-1,2": 0.1})
    assert parsed == {(3, 4): 0.9, (-1, 2): 0.1}


def test_fresh_tracker_is_fuzzy():
    assert Tracker().estimate() == (None, FUZZY)
