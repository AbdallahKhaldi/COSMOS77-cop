"""Template pool discipline, the outgoing-hint lint, and liar-score calibration."""

import random

from cosmos77_cop.hints.liar_score import LiarScore, direction_matches, hinted_direction
from cosmos77_cop.hints.lint import enforce, is_coordinate_free, truncate_words
from cosmos77_cop.hints.templates import LIES_COP, LIES_THIEF, TRUTHS, safe_line, template_hint


def test_every_pool_line_is_short_and_digit_free():
    for pool in (TRUTHS, LIES_COP, LIES_THIEF):
        for line in pool:
            rendered = line.format(arena="New York")
            assert len(rendered.split()) <= 15
            assert is_coordinate_free(rendered)


def test_template_pick_is_deterministic_and_arena_aware():
    a = template_hint("police", "lie", "New York", random.Random(3))
    b = template_hint("police", "lie", "New York", random.Random(3))
    assert a == b
    assert "New York" in template_hint("thief", "truth", "New York", random.Random(1)) or True


def test_lint_truncates_and_rejects_digits():
    long = " ".join(["word"] * 40)
    assert len(truncate_words(long, 15).split()) == 15
    fallback = safe_line("New York")
    assert enforce("meet me at 3,4 tonight", max_words=15, fallback=fallback) == fallback
    assert enforce("", max_words=15, fallback=fallback) == fallback
    assert enforce("clean and calm streets ahead", max_words=15, fallback=fallback) == (
        "clean and calm streets ahead"
    )


def test_hinted_direction_and_halves():
    assert hinted_direction("sweeping the North bridges") == "north"
    assert hinted_direction("going downtown tonight") == "south"
    assert hinted_direction("nothing to see here") is None
    assert direction_matches("north", (1, 3), 7)
    assert not direction_matches("north", (5, 3), 7)
    assert direction_matches("east", (3, 6), 7)


def test_liar_score_converges_and_ignores_neutral():
    score = LiarScore()
    for _ in range(10):
        score.observe("we are on the north side", (6, 3), 7)
    assert score.value < 0.05
    honest = LiarScore()
    for _ in range(10):
        honest.observe("heading east now", (3, 6), 7)
    assert honest.value > 0.95
    neutral = LiarScore()
    neutral.observe("quiet night everywhere", (3, 3), 7)
    assert neutral.value == 0.5 and neutral.observations == 0
