"""Kit vector conformance, extension tier: consensus, locks, declarations, the book scent model."""

import json
from pathlib import Path

import pytest

from cosmos77_cop.protocol.canonical import canonical_hash
from cosmos77_cop.protocol.consensus import (
    CONSENSUS_KEY,
    report_consensus_signature,
    sign_report,
    verify_report,
)
from cosmos77_cop.protocol.locks import REGISTERED, lock_conflicts
from cosmos77_cop.protocol.pairing import pairing_decision, uid_decision
from cosmos77_cop.protocol.scent import BOOK_KERNEL, book_delta, book_update, book_update_field

VECTORS = Path(__file__).resolve().parents[1] / "vectors"


def load(name: str) -> dict:
    return json.loads((VECTORS / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", load("report_consensus")["vectors"], ids=lambda c: c["note"][:30])
def test_report_consensus_vectors(case):
    assert report_consensus_signature(case["report"]) == case["signature"]
    assert sign_report(case["report"]) == case["signed_report"]
    assert verify_report(case["signed_report"])
    assert canonical_hash(case["report"]) == case["compact_form_sha256"]
    broken = dict(case["signed_report"])
    broken[CONSENSUS_KEY] = "0" * 64
    assert not verify_report(broken)


def test_locked_model_registered_docs_hash_to_pinned_values():
    for entry in load("locked_model")["registered"]:
        assert canonical_hash(entry["doc"]) == entry["sha256"]
        key = (entry["doc"]["family"], entry["doc"]["name"])
        if key in REGISTERED:
            assert REGISTERED[key] == entry["sha256"]


@pytest.mark.parametrize("case", load("locked_model")["refusal_rule"], ids=lambda c: c["note"][:40])
def test_locked_model_refusal_table(case):
    conflicts = lock_conflicts({"scent_model": case["ours"]}, {"scent_model": case["theirs"]})
    decision = "refuse" if conflicts else "play"
    assert decision == case["decision"]


@pytest.mark.parametrize(
    "case", load("uid_declaration")["refusal_rule"], ids=lambda c: c["note"][:40]
)
def test_uid_declaration_table(case):
    assert uid_decision(case["ours"], case["theirs"]) == case["decision"]


def test_uid_worked_example_flat_vs_wider_config():
    from cosmos77_cop.protocol.ids import game_uid

    w = load("uid_declaration")["worked_example"]
    a, b = w["group_ids"]
    assert game_uid(w["flat_terms"], a, b) == w["from_flat_terms"]
    assert game_uid(w["wider_config"], a, b) == w["from_a_wider_config"]
    assert w["from_flat_terms"] != w["from_a_wider_config"]


@pytest.mark.parametrize(
    "case", load("pairing_declaration")["refusal_rule"], ids=lambda c: c["note"][:40]
)
def test_pairing_declaration_table(case):
    assert pairing_decision(case["ours"], case["theirs"]) == case["decision"]


def test_book_kernel_is_verbatim():
    fixture = load("scent_book_v3")
    kernel = fixture["model"]["params"]["kernel"]
    assert [list(row) for row in BOOK_KERNEL] == kernel


@pytest.mark.parametrize("case", load("scent_book_v3")["emit"], ids=lambda c: c["note"][:30])
def test_book_emit_from_empty_field(case):
    fixture = load("scent_book_v3")
    rho = fixture["model"]["params"]["decay_rho"]
    board = fixture["field_walk"]["board_size"]
    field = book_update_field({}, book_delta(tuple(case["center"]), board), rho)
    assert {f"{r},{c}": v for (r, c), v in field.items()} == case["field"]


def test_book_scalar_traces_bit_exact():
    traces = load("scent_book_v3")["scalar_traces"]
    assert book_update(traces["pure_decay"]["tau"], traces["pure_decay"]["delta"], 0.1) == (
        traces["pure_decay"]["after"]
    )
    assert book_update(traces["clamp"]["tau"], traces["clamp"]["delta"], 0.1) == (
        traces["clamp"]["after"]
    )
    tau = 0.0
    for step in traces["chain"]["steps"]:
        tau = book_update(tau, step["delta"], 0.1)
        assert tau == step["tau"]


def test_book_evaluation_order_is_the_pinned_one():
    for case in load("scent_book_v3")["ordering_probe"]["cases"]:
        ours = (1 - 0.1) * case["tau"] + case["delta"]
        assert ours == case["pinned_order"]
        assert book_update(case["tau"], case["delta"], 0.1) == min(case["pinned_order"], 0.9)


def test_book_field_walk_three_turns():
    walk = load("scent_book_v3")["field_walk"]
    field: dict = {}
    for turn in walk["turns"]:
        delta = book_delta(tuple(turn["center"]), walk["board_size"])
        field = book_update_field(field, delta, walk["rho"])
        assert {f"{r},{c}": v for (r, c), v in field.items()} == turn["field"]
