"""The settlement preimage is the reference's FIVE-key row — pinned so it cannot drift back.

The kit itself documented a six-key row (with ``tie``) from 2026-08-04 to 08-13 — the exact
window this project was built in — and this repo shipped it.  Every hash ever settled live
reproduces only under five keys; a six-key signer fails settlement against every played
implementation, and on a counted series that is rule 35: zero for BOTH teams.
"""

from __future__ import annotations

from cosmos77_cop.protocol.consensus import consensus_scope

ROW = {
    "sub_game_number": 1,
    "roles": {"a": "police", "b": "thief"},
    "result": "survival",
    "winner_group": "b",
    "tie": False,          # document row keeps it; the HASH row must not
    "score": {"a": 5, "b": 10},
    "timestamp": "2026-08-15T00:00:00+00:00",   # per-side, never signed
    "tokens": {"a": 900, "b": 0},               # per-side, never signed
}


def test_the_hash_row_is_exactly_the_reference_five_keys():
    scope = consensus_scope("g", {"total": 1}, [ROW])
    assert sorted(scope["sub_games"][0]) == [
        "result", "roles", "score", "sub_game_number", "winner_group",
    ], "the preimage row drifted from the reference's five-key form (kit SPEC §6)"


def test_tie_never_reenters_the_preimage():
    """The regression that was live 08-04 to 08-13: tie signed into the row."""
    scope = consensus_scope("g", {}, [ROW])
    assert "tie" not in scope["sub_games"][0]
    assert "timestamp" not in scope["sub_games"][0]
    assert "tokens" not in scope["sub_games"][0]


def test_a_sparse_row_signs_only_what_it_has():
    scope = consensus_scope("g", {}, [{"sub_game_number": 2, "result": "capture"}])
    assert scope["sub_games"][0] == {"sub_game_number": 2, "result": "capture"}
