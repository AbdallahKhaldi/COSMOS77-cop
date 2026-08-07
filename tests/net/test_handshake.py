"""Handshake refusal codes SPAR-N00..N10, bystander semantics, omission-never-refuses."""

import json
from pathlib import Path

from cosmos77_cop.net.handshake import build_greeting, peer_group_id, verify_peer
from cosmos77_cop.protocol.locks import OUR_LOCKS
from cosmos77_cop.protocol.terms import terms_from_config

REPO_ROOT = Path(__file__).resolve().parents[2]
TERMS = terms_from_config(
    json.loads((REPO_ROOT / "config" / "game.json").read_text(encoding="utf-8"))
)
UID = "a6ae6e70-9da2-f5cc-f365-443f077b9e1c"


def greeting(**overrides):
    base = build_greeting(
        terms=dict(TERMS),
        nonce="ab" * 16,
        group_id="opponent-x",
        role="thief",
        sub_game_number=1,
        identity={"group_id": "opponent-x", "members": []},
        locks=dict(OUR_LOCKS),
        game_uid=None,
    )
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def ours(**overrides):
    base = build_greeting(
        terms=dict(TERMS),
        nonce="cd" * 16,
        group_id="cosmos77",
        role="police",
        sub_game_number=1,
        identity={"group_id": "cosmos77", "members": []},
        locks=dict(OUR_LOCKS),
        game_uid=None,
    )
    base.update(overrides)
    return base


def verify(theirs, our_uid=None, our=None):
    return verify_peer(ours=our or ours(), theirs=theirs, our_uid=our_uid)


def test_clean_greeting_plays():
    v = verify(greeting())
    assert v.ok and v.code is None


def test_n00_not_an_object():
    assert verify("hello").code == "SPAR-N00"


def test_n01_terms_absent_names_the_keys_we_got():
    v = verify({"nonce": "x", "role": "thief"})
    assert v.code == "SPAR-N01" and "wire-shape" in v.detail


def test_n02_terms_incomplete():
    g = greeting()
    del g["terms"]["setting"]
    v = verify(g)
    assert v.code == "SPAR-N02" and "setting" in v.detail


def test_n03_terms_differ_shows_both_canonical_strings():
    g = greeting()
    g["terms"] = {**g["terms"], "setting": "Haifa"}
    v = verify(g)
    assert v.code == "SPAR-N03" and "Haifa" in v.detail and "ours=" in v.detail


def test_n04_bad_signature_points_at_serialization():
    g = greeting()
    g["signature"] = "0" * 64
    v = verify(g)
    assert v.code == "SPAR-N04" and "ensure_ascii" in v.detail


def test_n05_lock_conflict_only_when_both_declare():
    g = greeting(scent_model_sha256="f" * 64)
    assert verify(g).code == "SPAR-N05"
    silent = greeting()
    del silent["scent_model_sha256"]
    assert verify(silent).ok


def test_n06_sub_game_mismatch_is_bystander():
    v = verify(greeting(sub_game_number=5))
    assert v.code == "SPAR-N06" and v.bystander


def test_n07_role_collision_is_bystander():
    v = verify(greeting(role="police"))
    assert v.code == "SPAR-N07" and v.bystander


def test_n08_no_group_id_anywhere():
    g = greeting()
    del g["group_id"]
    g["identity"] = {}
    assert verify(g).code == "SPAR-N08"


def test_n10_uid_mismatch_only_when_both_declare():
    other = "5db600b1-0bce-2aeb-4068-2717f6032be0"
    assert verify(greeting(game_uid=other), our_uid=UID).code == "SPAR-N10"
    assert verify(greeting(game_uid=UID), our_uid=UID).ok
    assert verify(greeting(), our_uid=UID).ok
    assert verify(greeting(game_uid=other), our_uid=None).ok


def test_omission_never_refuses_reference_shaped_minimal_greeting():
    minimal = {
        "terms": dict(TERMS),
        "nonce": "ab" * 16,
        "signature": greeting()["signature"],
        "group_id": "opponent-x",
    }
    assert verify(minimal).ok


def test_peer_group_id_prefers_top_level():
    assert peer_group_id(greeting()) == "opponent-x"
    assert peer_group_id({"identity": {"group_id": "deep"}}) == "deep"
