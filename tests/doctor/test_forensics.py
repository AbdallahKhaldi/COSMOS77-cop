"""Forensics pinned to the kit's real divergent-form vectors (commit_reveal.json)."""

import hashlib
import json

from cosmos77_cop.doctor.forensics import forensics_stage, identify_dialect
from cosmos77_cop.protocol.consensus import spaced_str

# vectors/commit_reveal.json divergent_forms — real pinned bytes, restated here
PAYLOAD = {
    "step": 1,
    "state": "grid=7x7;self=[4, 3];barriers=[]",
    "position": [4, 3],
    "move": "MOVE:S",
    "intent": "truth",
    "hint": "I keep to the main avenues.",
}
NONCE = "112233445566778899aabbccddeeff00"
REFERENCE_FORM = "aa6420e2d3a907d6c140856caecbb351b4d5ad98e381549c28268669af378dcc"
BOOK_LISTING_FORM = "833e47c675448a9072660b984d8514a5786792372f415caea1b0d4348b301875"
BOOK_AUDIT_SNIPPET = "8041fe9546f17d67b1c60b881b79daf20f932a2dcbc7ee87fb92c4c1bdfaa9a0"

# vectors/terms_signature.json — the CORE greeting-signature vector
TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14, "setting": "Haifa",
    "hint_max_words": 15, "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 1,
}
TERMS_NONCE = "a1a2a3a4b1b2b3b4c1c2c3c4d1d2d3d4"
TERMS_SIG = "80793141f22b6193b02a74d5955767ad1e24abbac172894358ec13622b85a04c"


def test_reference_form_identified_as_reference():
    name, _ = identify_dialect(PAYLOAD, NONCE, REFERENCE_FORM)
    assert name == "reference_compact"


def test_kit_book_listing_form_is_nonce_inside_compact():
    name, fix = identify_dialect(PAYLOAD, NONCE, BOOK_LISTING_FORM)
    assert name == "nonce_inside_compact"
    assert "pipe-append" in fix


def test_kit_audit_snippet_form_is_nonce_move_only():
    name, fix = identify_dialect(PAYLOAD, NONCE, BOOK_AUDIT_SNIPPET)
    assert name == "nonce_move_only"
    assert "FULL" in fix


def test_spaced_separator_dialect_names_the_book_ch5_fix():
    observed = hashlib.sha256(f"{spaced_str(PAYLOAD)}|{NONCE}".encode()).hexdigest()
    name, fix = identify_dialect(PAYLOAD, NONCE, observed)
    assert name == "book_ch5_spaced"
    assert "compact separators (',',':')" in fix


def test_ascii_escaped_dialect_detected_on_non_ascii_payload():
    payload = {"hint": "אני ליד הכיכר", "move": "MOVE:N"}
    escaped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    observed = hashlib.sha256(f"{escaped}|{NONCE}".encode()).hexdigest()
    name, fix = identify_dialect(payload, NONCE, observed)
    assert name == "ascii_escaped"
    assert "ensure_ascii=False" in fix


def test_stage_green_when_signature_verifies_reference():
    stage = forensics_stage({"terms": TERMS, "nonce": TERMS_NONCE, "signature": TERMS_SIG})
    assert stage.status == "green"
    assert "reference dialect" in stage.finding


def test_stage_yellow_names_dialect_for_spaced_signature():
    observed = hashlib.sha256(f"{spaced_str(TERMS)}|{TERMS_NONCE}".encode()).hexdigest()
    stage = forensics_stage({"terms": TERMS, "nonce": TERMS_NONCE, "signature": observed})
    assert stage.status == "yellow"
    assert stage.detail["matched_dialect"] == "book_ch5_spaced"
    assert "spaced separators (book ch.5 form)" in stage.fix_line


def test_stage_red_with_raw_compare_when_nothing_matches():
    stage = forensics_stage({"payload": PAYLOAD, "nonce": NONCE, "commit": "f" * 64})
    assert stage.status == "red"
    assert stage.detail["observed"] == "f" * 64
    assert set(stage.detail["expected_per_dialect"]) >= {
        "reference_compact", "book_ch5_spaced", "nonce_inside_compact", "nonce_move_only"
    }
    assert stage.detail["expected_per_dialect"]["reference_compact"] == REFERENCE_FORM


def test_stage_skips_without_a_sample_or_with_a_partial_sample():
    assert forensics_stage(None).status == "green"
    assert "skipped" in forensics_stage(None).finding
    assert "skipped" in forensics_stage({"terms": TERMS}).finding
