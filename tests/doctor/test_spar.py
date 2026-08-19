"""Handshake stage: ok-acknowledged, SPAR refusals as diagnoses, transport failure, no crash."""

from types import SimpleNamespace

import pytest

from cosmos77_cop.doctor.spar import SPAR_DIAGNOSES, handshake_stage
from cosmos77_cop.net.client import PeerCallError

GREETING = {"terms": {}, "nonce": "0" * 32, "signature": "s"}


def test_every_code_n00_to_n10_has_a_diagnosis():
    codes = {f"SPAR-N{n:02d}" for n in range(11)}
    assert codes == set(SPAR_DIAGNOSES)
    assert "wire-shape fault on the SENDER" in SPAR_DIAGNOSES["SPAR-N01"]
    assert "ensure_ascii" in SPAR_DIAGNOSES["SPAR-N04"]
    assert "restart exactly one side" in SPAR_DIAGNOSES["SPAR-N07"]
    assert "WIDER input" in SPAR_DIAGNOSES["SPAR-N10"]


def test_ok_true_acknowledgement_is_yellow():
    stage = handshake_stage("u", lambda url, g: SimpleNamespace(data={"ok": True}), GREETING)
    assert stage.status == "yellow"
    assert "NOT returned" in stage.finding
    assert stage.detail["data"] == {"ok": True}


def test_refusal_code_in_transport_error_is_yellow_diagnosis_not_crash():
    def caller(url, greeting):
        raise PeerCallError("negotiate: refused — SPAR-N04: signature does not verify")
    stage = handshake_stage("u", caller, GREETING)
    assert stage.status == "yellow"
    assert stage.detail["refusal"] == "SPAR-N04"
    assert "serialization" in stage.fix_line


def test_refusal_code_inside_a_returned_payload_is_yellow():
    result = SimpleNamespace(data={"refused": "SPAR-N07 role collision"})
    stage = handshake_stage("u", lambda url, g: result, GREETING)
    assert stage.status == "yellow"
    assert stage.detail["refusal"] == "SPAR-N07"
    assert "restart exactly one side" in stage.finding


def test_plain_transport_failure_is_red_with_fix():
    def caller(url, greeting):
        raise PeerCallError("negotiate: All connection attempts failed")
    stage = handshake_stage("u", caller, GREETING)
    assert stage.status == "red"
    assert "negotiate call failed" in stage.finding
    assert "tools/call" in stage.fix_line


def test_no_url_skips():
    stage = handshake_stage(None, None, GREETING)
    assert stage.status == "green" and "skipped" in stage.finding


@pytest.mark.parametrize("weird", [SimpleNamespace(data=None, content=[{"text": "hi"}]), "raw"])
def test_non_reference_responses_never_crash(weird):
    """Odd shapes must not crash — and a reply with NO greeting is honestly YELLOW now
    (two live windows died behind the old green; see test_handshake_honesty)."""
    stage = handshake_stage("u", lambda url, g: weird, GREETING)
    assert stage.status == "yellow"
    assert stage.detail["response"]
