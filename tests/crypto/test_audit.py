"""Audit layers 1-3: integrity, binding, physics — each verdict provoked and distinguished."""

from cosmos77_cop.crypto.audit import (
    VERDICT_ILLEGAL,
    VERDICT_TAMPERED,
    VERDICT_VERIFIED,
    audit_records,
)
from cosmos77_cop.protocol.canonical import canonical_hash
from cosmos77_cop.protocol.sealing import build_turn_payload, commit

PHYSICS = {"grid_size": 7, "barriers_max": 14, "max_steps": 35}


def make_log(positions, *, role="thief"):
    records, received = [], {}
    for step, pos in enumerate(positions, start=1):
        payload = build_turn_payload(
            step=step,
            role=role,
            sub_game=1,
            grid_size=7,
            self_pos=pos,
            barriers=[],
            move="MOVE:S",
            intent="truth",
            hint="calm streets",
            verdict="moved",
        )
        nonce = f"{step:032x}"
        sealed = commit(payload, nonce)
        records.append({"payload": payload, "nonce": nonce, "commit": sealed})
        received[step] = sealed
    return records, received


def test_clean_log_verifies():
    records, received = make_log([(4, 3), (5, 3), (5, 4)])
    report = audit_records(records, received, **PHYSICS)
    assert report.verdict == VERDICT_VERIFIED
    assert report.clean


def test_one_flipped_byte_is_tampered():
    records, received = make_log([(4, 3), (5, 3)])
    records[1]["payload"]["hint"] = "calm streets!"
    report = audit_records(records, received, **PHYSICS)
    assert report.verdict == VERDICT_TAMPERED
    assert 2 in report.failed_steps


def test_wholesale_reforged_log_fails_binding_not_integrity():
    records, received = make_log([(4, 3), (5, 3)])
    forged_payload = dict(records[1]["payload"])
    forged_payload["position"] = [6, 6]
    forged_payload["state"] = "grid=7x7;self=[6, 6];barriers=[]"
    nonce = records[1]["nonce"]
    forged_commit = commit(forged_payload, nonce)
    records[1] = {"payload": forged_payload, "nonce": nonce, "commit": forged_commit}
    report = audit_records(records, received, **PHYSICS)
    assert report.verdict == VERDICT_TAMPERED
    assert any("differs from the one received" in n for n in report.notes)


def test_received_but_never_revealed_is_tampered():
    records, received = make_log([(4, 3), (5, 3)])
    report = audit_records(records[:1], received, **PHYSICS)
    assert report.verdict == VERDICT_TAMPERED
    assert any("never revealed" in n for n in report.notes)


def test_illegal_trail_is_illegal_not_tampered():
    records, received = make_log([(4, 3), (6, 6)])
    report = audit_records(records, received, **PHYSICS)
    assert report.verdict == VERDICT_ILLEGAL
    assert any("not one orthogonal step" in n for n in report.notes)


def test_off_board_position_is_illegal():
    records, received = make_log([(4, 3), (4, 4)])
    records[1]["payload"]["position"] = [7, 3]
    records[1]["commit"] = commit(records[1]["payload"], records[1]["nonce"])
    received[2] = records[1]["commit"]
    report = audit_records(records, received, **PHYSICS)
    assert report.verdict == VERDICT_ILLEGAL


def test_degraded_reveal_without_positions_verifies_with_note():
    payload = {"step": 1, "sealed": canonical_hash({"anything": 1})}
    nonce = "ab" * 16
    records = [{"payload": payload, "nonce": nonce, "commit": commit(payload, nonce)}]
    report = audit_records(records, {1: records[0]["commit"]}, **PHYSICS)
    assert report.verdict == VERDICT_VERIFIED
    assert any("degraded" in n for n in report.notes)


def test_book_ch5_sealed_log_is_flagged_tampered():
    records, _received = make_log([(4, 3)])
    payload, nonce = records[0]["payload"], records[0]["nonce"]
    records[0]["commit"] = canonical_hash({**payload, "nonce": nonce})
    report = audit_records(records, {1: records[0]["commit"]}, **PHYSICS)
    assert report.verdict == VERDICT_TAMPERED
