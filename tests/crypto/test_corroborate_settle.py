"""Audit layer 4 (concession/answer corroboration) and the settlement rule."""

from cosmos77_cop.crypto.audit import VERDICT_TAMPERED, VERDICT_VERIFIED, AuditReport
from cosmos77_cop.crypto.corroborate import corroborate_capture
from cosmos77_cop.crypto.settle import settled_outcome


def test_answer_echoing_our_claim_corroborates():
    ok, reason = corroborate_capture(
        {"claim": [2, 3], "caught": True},
        trail_end=(2, 3),
        cop_claimed_cell=(2, 3),
        barrier_cells=set(),
        grid_size=7,
    )
    assert ok and "answer" in reason


def test_rule46_concession_needs_our_barrier_record():
    ok, reason = corroborate_capture(
        {"claim": [4, 4], "caught": True},
        trail_end=(4, 4),
        cop_claimed_cell=None,
        barrier_cells={(4, 4)},
        grid_size=7,
    )
    assert ok and "rule-46" in reason


def test_rule47_concession_needs_boxedness_under_our_barriers():
    ok, reason = corroborate_capture(
        {"claim": [0, 0], "caught": True},
        trail_end=(0, 0),
        cop_claimed_cell=None,
        barrier_cells={(0, 1), (1, 0)},
        grid_size=7,
    )
    assert ok and "rule 47" in reason


def test_false_concession_is_rejected():
    ok, reason = corroborate_capture(
        {"claim": [3, 3], "caught": True},
        trail_end=(3, 3),
        cop_claimed_cell=None,
        barrier_cells={(0, 1)},
        grid_size=7,
    )
    assert not ok and "neither" in reason


def test_trail_contradicting_the_concession_is_rejected():
    ok, reason = corroborate_capture(
        {"claim": [4, 4], "caught": True},
        trail_end=(2, 2),
        cop_claimed_cell=None,
        barrier_cells={(4, 4)},
        grid_size=7,
    )
    assert not ok and "trail ends" in reason


def test_degraded_reveal_without_trail_still_corroborates_on_barriers():
    ok, _ = corroborate_capture(
        {"claim": [4, 4], "caught": True},
        trail_end=None,
        cop_claimed_cell=None,
        barrier_cells={(4, 4)},
        grid_size=7,
    )
    assert ok


CLEAN = AuditReport(VERDICT_VERIFIED)
FAILED = AuditReport(VERDICT_TAMPERED, [2], ["step 2: mismatch"])


def test_exchanged_and_clean_stands():
    s = settled_outcome("capture", CLEAN, their_audit_arrived=True)
    assert s.settled and s.result == "capture" and s.log_verified and not s.tampered


def test_exchanged_and_failed_is_tamper_forfeit():
    s = settled_outcome("survival", FAILED, their_audit_arrived=True)
    assert s.settled and s.result == "tamper_forfeit" and s.tampered


def test_no_audit_on_zeroed_outcome_settles_technical_row():
    s = settled_outcome("technical_loss", None, their_audit_arrived=False)
    assert s.settled and s.result == "technical_loss"
    assert not s.log_verified and not s.tampered


def test_no_audit_on_played_outcome_is_not_settled_nothing_sent():
    s = settled_outcome("capture", None, their_audit_arrived=False)
    assert not s.settled and s.result is None
