"""A hostile reveal is a verdict, never a crash (audit-records-crash-on-hostile-reveal)."""

from __future__ import annotations

from cosmos77_cop.crypto.audit import VERDICT_TAMPERED, audit_records


def _run(records):
    return audit_records(records, {}, grid_size=7, barriers_max=14, max_steps=35)


def test_non_dict_elements_are_tampered_not_a_crash():
    report = _run(["garbage", 42, None])
    assert report.verdict == VERDICT_TAMPERED
    assert "malformed" in report.notes[0]


def test_payload_not_a_dict_is_tampered_not_a_crash():
    report = _run([{"payload": "not-a-dict", "nonce": "aa", "commit": "bb"}])
    assert report.verdict == VERDICT_TAMPERED


def test_unintable_step_is_tampered_not_a_crash():
    report = _run([{"payload": {"step": {"nested": 1}}, "nonce": "aa", "commit": "bb"}])
    assert report.verdict == VERDICT_TAMPERED


def test_records_not_a_list_is_tampered_not_a_crash():
    report = _run({"records": "should have been a list"})
    assert report.verdict == VERDICT_TAMPERED


def test_a_sound_reveal_still_verifies_after_the_guard():
    from cosmos77_cop.protocol.sealing import commit

    payload = {"step": 1, "role": "police"}
    report = _run([{"payload": payload, "nonce": "ab" * 16,
                    "commit": commit(payload, "ab" * 16)}])
    assert report.clean
