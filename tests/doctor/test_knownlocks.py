"""KNOWN_LOCKS identification: matching/different/unknown/omitted, kit hashes covered."""

from cosmos77_cop.doctor.knownlocks import KNOWN_LOCKS, extract_locks, locks_stage
from cosmos77_cop.protocol.locks import OUR_LOCKS, REGISTERED

SUBTRACTIVE = REGISTERED[("scent_model", "subtractive_chebyshev_v1")]
MULTIPLICATIVE = REGISTERED[("scent_model", "multiplicative_book_v1")]
WIRE_REF = REGISTERED[("wire_shape", "reference-v3")]
BELIEF = REGISTERED[("info_mode", "belief")]


def test_table_covers_registered_and_kit_pinned_forms():
    for digest in (SUBTRACTIVE, MULTIPLICATIVE, WIRE_REF, BELIEF):
        assert digest in KNOWN_LOCKS
    kinds = {v["kind"] for v in KNOWN_LOCKS.values()}
    assert kinds == {"scent_model", "wire_shape", "info_mode", "smell_binding"}
    # the kit's divergent/PROPOSED forms are identifiable too
    assert sum(v["kind"] == "wire_shape" for v in KNOWN_LOCKS.values()) == 2
    assert sum(v["kind"] == "info_mode" for v in KNOWN_LOCKS.values()) == 2
    assert sum(v["kind"] == "smell_binding" for v in KNOWN_LOCKS.values()) == 2


def test_extract_locks_reads_only_family_sha_keys():
    greeting = {
        "terms": {}, "signature": "x",
        "scent_model_sha256": SUBTRACTIVE, "wire_shape_sha256": WIRE_REF,
    }
    assert extract_locks(greeting) == {
        "scent_model": SUBTRACTIVE, "wire_shape": WIRE_REF
    }


def test_all_matching_is_green():
    stage = locks_stage(
        {f"{family}_sha256": digest for family, digest in OUR_LOCKS.items()}
    )
    assert stage.status == "green"
    assert "matches ours" in stage.finding


def test_known_but_different_scent_is_yellow_with_auto_adapt():
    stage = locks_stage({"scent_model_sha256": MULTIPLICATIVE})
    assert stage.status == "yellow"
    assert "multiplicative_book_v1" in stage.finding
    assert "--scent-model multiplicative_book_v1" in stage.fix_line


def test_known_but_different_wire_shape_is_yellow_without_scent_adapt():
    bookletter = next(
        digest for digest, meta in KNOWN_LOCKS.items()
        if meta["name"].startswith("bookletter-v3")
    )
    stage = locks_stage({"wire_shape_sha256": bookletter})
    assert stage.status == "yellow"
    assert "bookletter-v3" in stage.finding
    assert "reference-v3" in stage.fix_line


def test_unknown_hash_is_red_and_asks_for_the_doc():
    stage = locks_stage({"scent_model_sha256": "ab" * 32})
    assert stage.status == "red"
    assert "UNKNOWN" in stage.finding
    assert "locked_model schema" in stage.fix_line


def test_family_we_do_not_declare_is_green_omission_never_refuses():
    none_binding = next(
        digest for digest, meta in KNOWN_LOCKS.items()
        if meta["kind"] == "smell_binding" and meta["name"].startswith("none")
    )
    stage = locks_stage({"smell_binding_sha256": none_binding})
    assert stage.status == "green"
    assert "omission never refuses" in stage.finding


def test_no_greeting_observed_is_green_with_capture_hint():
    stage = locks_stage(None)
    assert stage.status == "green"
    assert "--their-greeting" in stage.finding
    assert stage.detail["ours"] == dict(OUR_LOCKS)
