"""A4/A6: the sealed intent is MEASURED after the fact, and the token budget is a hard stop.

The audit scored a live series and found 31% of hints declared ``lie`` while the statement was
TRUE about our own half — the flag was drawn from an RNG before any text existed. It also found
nothing anywhere comparing consumption against the negotiated ``token_budget_per_series``.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from cosmos77_cop.hints.gemini import GeminiHinter, HintMeter
from cosmos77_cop.hints.liar_score import declared_intent, direction_matches, hinted_direction
from cosmos77_cop.hints.provider import HintProvider
from cosmos77_cop.hints.templates import TRUTHS

NORTH = "Half the squad is sweeping the north bridges of New York tonight."
VACUOUS = "Still on the move, same as every turn in New York."


def provider(**kw):
    base = dict(
        role="police", arena="New York", max_words=15, grid_size=7,
        token_budget=1000, seed=11,
    )
    return HintProvider(**{**base, **kw})


def hinter(tokens=42, text="The west side is sealed tight tonight"):
    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        text=text, usage_metadata=SimpleNamespace(total_token_count=tokens)
    )
    meter = HintMeter()
    h = GeminiHinter("k", "m", meter)
    h._client = client
    return h, meter, client


def test_declared_intent_is_measured_against_the_cell_we_actually_seal():
    assert declared_intent(NORTH, (1, 3), 7, "lie") == "truth", "true statement sealed as a bluff"
    assert declared_intent(NORTH, (5, 3), 7, "lie") == "lie"
    assert declared_intent(NORTH, (1, 3), 7, "truth") == "truth"
    assert declared_intent(NORTH, (5, 3), 7, "truth") == "lie", "a bluff may never seal as truth"


def test_a_line_committing_to_nothing_keeps_the_bluff_policys_own_label():
    assert hinted_direction(VACUOUS) is None
    assert declared_intent(VACUOUS, (0, 0), 7, "lie") == "lie"
    assert declared_intent(VACUOUS, (0, 0), 7, "truth") == "truth"


def test_no_truth_pool_line_makes_a_checkable_positional_claim():
    """TRUTHS once said "near the middle of {arena}" — truth-flagged from a corner."""
    banned = ("middle", "center", "centre", "north", "south", "east", "west",
              "uptown", "downtown")
    for line in TRUTHS:
        lowered = line.format(arena="New York").lower()
        assert not any(word in lowered for word in banned), f"positional TRUTHS line: {line}"


def test_scored_replay_over_every_cell_has_zero_mis_declarations():
    mis = 0
    for seed in range(12):
        chain = provider(seed=seed)
        for step, cell in enumerate([(r, c) for r in range(7) for c in range(7)], start=1):
            result = chain.hint_for_step(step, sub_game=1, cell=cell)
            direction = hinted_direction(result.text)
            if direction is not None:
                truthful = direction_matches(direction, cell, 7)
                mis += int(truthful != (result.intent == "truth"))
    assert mis == 0, f"{mis} hints declared an intent the statement does not support"


def test_the_bluff_policy_still_draws_from_both_pools():
    chain = provider(lie_rate=0.75)
    seen = {chain.hint_for_step(s, sub_game=1, cell=(3, 3)).intent for s in range(1, 25)}
    assert seen == {"truth", "lie"}


def test_gemini_stops_for_the_rest_of_the_series_once_the_budget_is_crossed():
    hint, meter, client = hinter(tokens=40)
    chain = provider(gemini=hint, every_n_steps=1, token_budget=100)
    for step in range(1, 8):
        chain.hint_for_step(step, sub_game=1, cell=(3, 3))
    assert client.models.generate_content.call_count == 3, "the budget never stopped the calls"
    assert meter.series_total == 120


def test_tokens_spent_in_earlier_sub_games_count_against_the_same_budget():
    hint, meter, client = hinter(tokens=40)
    meter.carried = 90
    chain = provider(gemini=hint, every_n_steps=1, token_budget=100)
    for step in range(1, 5):
        chain.hint_for_step(step, sub_game=2, cell=(3, 3))
    assert client.models.generate_content.call_count == 1
    assert meter.series_total == 130
    assert meter.total_sub_game == 40, "the per-sub-game counter must not absorb the carry"


def test_the_word_cap_reaches_the_prompt_instead_of_a_hardcoded_fifteen():
    hint, _meter, client = hinter()
    provider(gemini=hint, every_n_steps=1, max_words=10).hint_for_step(
        1, sub_game=1, cell=(3, 3)
    )
    sent = client.models.generate_content.call_args.kwargs["contents"]
    assert "under 10 words" in sent and "under 15 words" not in sent
