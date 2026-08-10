"""The sealed window log must carry the audit VERDICT, not only its boolean shadow.

All four audit layers run and all four catch tampering — but a grader opening ``log_*.json``
used to see `log_verified: true` and nothing else. These pin the evidence into the artifact.
"""

import json
import types

from cosmos77_cop.crypto.audit import AuditReport
from cosmos77_cop.crypto.settle import Settlement
from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.orchestrator.serieslog import NO_AUDIT, audit_block, write_window_log
from cosmos77_cop.orchestrator.subreport import SubGameReport
from cosmos77_cop.protocol.canonical import canonical_bytes
from cosmos77_cop.report.artifacts import ArtifactWriter

REPO = __import__("pathlib").Path(__file__).resolve().parents[2]


def a_report(my_audit, settlement, arrived=True):
    return SubGameReport(
        sub_game_number=1, my_role="police", result="capture", reason="caught", steps=4,
        started_at="t0", ended_at="t1", records=[], opp_records=[],
        my_audit=my_audit, their_audit_arrived=arrived, settlement=settlement,
    )


def test_a_clean_verdict_is_written_with_its_notes():
    verdict = AuditReport("verified", [], ["no position fields revealed - physics skipped"])
    block = audit_block(a_report(verdict, Settlement(True, "capture", True, False)))
    assert block["verdict"] == "verified"
    assert block["failed_steps"] == []
    assert block["notes"] == ["no position fields revealed - physics skipped"]
    assert block["their_audit_arrived"] is True


def test_a_tampered_verdict_names_the_steps_and_says_why():
    verdict = AuditReport("tampered", [5], ["step 5: revealed (payload, nonce) does not re-hash"])
    block = audit_block(a_report(verdict, Settlement(True, "tamper_forfeit", False, True)))
    assert block["verdict"] == "tampered" and block["failed_steps"] == [5]
    assert "re-hash" in block["notes"][0]


def test_no_reveal_is_a_null_verdict_never_a_silent_false():
    block = audit_block(a_report(None, Settlement(False, None, False, False), arrived=False))
    assert block["verdict"] is None and block["notes"] == [NO_AUDIT]
    assert block["their_audit_arrived"] is False


def test_the_verdict_survives_into_the_canonical_single_line_artifact(tmp_path):
    raw = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    writer = ArtifactWriter(
        tmp_path, gid="a-vs-b", uid="uid", github={}, counted=False, reason="friendly"
    )
    driver = types.SimpleNamespace(
        writer=writer, cfg=from_dict(raw), gid="a-vs-b", code_version="c" * 40,
        window_roles=lambda _w: ("cosmos77", "rival"),
    )
    verdict = AuditReport("illegal", [7], ["step 7: (0, 0) -> (4, 4) is not one orthogonal step"])
    report = a_report(verdict, Settlement(True, "tamper_forfeit", False, True))
    write_window_log(driver, 1, report)
    body = (tmp_path / "log_a-vs-b_g01.json").read_bytes()
    assert body.count(b"\n") == 1, "artifacts stay compact canonical bytes + one newline"
    log = json.loads(body)
    assert body == canonical_bytes(log) + b"\n"
    assert log["summary"]["audit"] == {
        "verdict": "illegal",
        "failed_steps": [7],
        "notes": ["step 7: (0, 0) -> (4, 4) is not one orthogonal step"],
        "their_audit_arrived": True,
    }
    assert log["summary"]["log_verified"] is False and log["summary"]["tampered"] is True
