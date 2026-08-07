"""Kit vector conformance, core tier: canonical form, commits, terms, ids, pheromone.

Every fixture under ``tests/vectors/`` is a verbatim copy of the community kit's executable
ground truth; these tests replay them against OUR implementations (PRD-6 gate).
"""

import hashlib
import json
from pathlib import Path

import pytest

from cosmos77_cop.protocol.canonical import canonical_hash, canonical_str
from cosmos77_cop.protocol.ids import artifact_filenames, game_id, game_uid
from cosmos77_cop.protocol.scent import merge_max, smell_decay, smell_emit
from cosmos77_cop.protocol.sealing import commit
from cosmos77_cop.protocol.terms import terms_signature

VECTORS = Path(__file__).resolve().parents[1] / "vectors"


def load(name: str) -> dict:
    return json.loads((VECTORS / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", load("canonical_json")["vectors"], ids=lambda c: c["note"][:40])
def test_canonical_json_vectors(case):
    assert canonical_str(case["object"]) == case["canonical"]
    assert canonical_hash(case["object"]) == case["sha256"]


@pytest.mark.parametrize("case", load("commit_reveal")["vectors"], ids=lambda c: c["note"][:40])
def test_commit_reveal_vectors(case):
    assert commit(case["payload"], case["nonce"]) == case["commit"]


def test_divergent_forms_only_reference_matches():
    d = load("commit_reveal")["divergent_forms"]
    ours = commit(d["payload"], d["nonce"])
    assert ours == d["reference_form"]
    assert ours != d["book_ch5_listing_form"]
    assert ours != d["book_audit_snippet_form"]
    ch5 = canonical_hash({**d["payload"], "nonce": d["nonce"]})
    assert ch5 == d["book_ch5_listing_form"]
    snippet = hashlib.sha256(f"{d['nonce']}|{d['payload']['move']}".encode()).hexdigest()
    assert snippet == d["book_audit_snippet_form"]


def test_terms_signature_vector():
    case = load("terms_signature")["vectors"][0]
    assert terms_signature(case["terms"], case["nonce"]) == case["signature"]


@pytest.mark.parametrize("case", load("game_uid")["vectors"], ids=lambda c: c["note"][:30])
def test_game_uid_and_id_vectors(case):
    assert game_uid(case["terms"], case["group_a"], case["group_b"]) == case["game_uid"]
    assert game_id(case["group_a"], case["group_b"]) == case["game_id"]


def test_artifact_filename_grammar():
    names = load("game_uid")["artifact_filenames"]
    ours = artifact_filenames("team-aleph-vs-team-bet")
    assert ours["declaration"] == names["declaration"]
    assert ours["result"] == names["result"]
    assert artifact_filenames("team-aleph-vs-team-bet", 3)["log"] == (
        "log_team-aleph-vs-team-bet_g03.json"
    )


@pytest.mark.parametrize("case", load("pheromone")["emit"], ids=lambda c: c["note"][:30])
def test_pheromone_emission_vectors(case):
    field = smell_emit(
        tuple(case["center"]), case["intensity"], case["grid_size"], case["board_size"]
    )
    assert field == case["field"]


@pytest.mark.parametrize("case", load("pheromone")["decay"], ids=lambda c: c["note"][:30])
def test_pheromone_decay_vectors(case):
    assert smell_decay(case["before"], case["decay"]) == case["after"]


def test_merge_by_max_keeps_the_stronger_trace():
    trail = {"3,3": 0.5, "2,2": 0.7}
    fresh = {"3,3": 0.9, "1,1": 0.3}
    assert merge_max(trail, fresh) == {"3,3": 0.9, "2,2": 0.7, "1,1": 0.3}
