"""The Gatekeeper matrix (rules 28-29) and the arming interlock (rules 32/35/37-38)."""

import inspect

import pytest

from cosmos77_cop import commands
from cosmos77_cop.report import recipients as rec
from cosmos77_cop.report.gatekeeper import (
    ALLOW,
    DENY_BUCKET,
    DENY_LOCKED,
    DENY_QUOTA,
    Gatekeeper,
    TokenBucket,
)
from cosmos77_cop.report.recipients import (
    FRIENDLY_INBOXES,
    LEAGUE_ADDRESS,
    ArmingError,
    Posture,
    assert_deliverable,
    recipients_for,
)


def test_token_bucket_refills_at_the_configured_rate():
    bucket = TokenBucket(rate_per_sec=0.5, capacity=2.0)
    assert bucket.take(0.0) and bucket.take(0.0)
    assert not bucket.take(0.0)
    assert not bucket.take(1.0)
    assert bucket.take(2.0)
    bucket.take(1000.0)
    assert bucket.tokens <= 2.0


def test_bucket_rate_derives_from_the_signed_requests_per_minute():
    keeper = Gatekeeper.from_config(requests_per_minute=30, capacity=5, daily_cap=20)
    assert keeper.rate_per_sec == 0.5


def test_daily_quota_denies_beyond_the_cap():
    keeper = Gatekeeper(daily_cap=2, dos_max_in_window=99)
    assert keeper.admit(0.0) == ALLOW
    assert keeper.admit(10.0) == ALLOW
    assert keeper.admit(20.0) == DENY_QUOTA
    assert keeper.check(30.0) == DENY_QUOTA


def test_empty_bucket_denies_without_burning_quota():
    keeper = Gatekeeper(rate_per_sec=0.0, capacity=1.0, daily_cap=10, dos_max_in_window=99)
    assert keeper.admit(0.0) == ALLOW
    assert keeper.admit(0.1) == DENY_BUCKET
    assert keeper.sent_today == 1


def test_dos_detector_locks_the_interface_and_stays_locked():
    keeper = Gatekeeper(rate_per_sec=100.0, capacity=100.0, daily_cap=99, dos_max_in_window=3)
    for now in (0.0, 0.1, 0.2):
        assert keeper.admit(now) == ALLOW
    assert keeper.admit(0.3) == DENY_LOCKED
    assert keeper.locked
    assert keeper.admit(9999.0) == DENY_LOCKED


def test_429_backoff_is_exponential_and_refunds_the_allowance():
    keeper = Gatekeeper()
    assert keeper.backoff_delays(3, 5.0) == [5.0, 10.0, 20.0]
    keeper.admit(0.0)
    before = keeper.sent_today
    keeper.note_rate_limited()
    assert keeper.sent_today == before - 1


def test_only_a_doubly_armed_posture_reaches_the_league_address():
    assert recipients_for(Posture(True, True)) == (LEAGUE_ADDRESS,)
    for posture in (Posture(False, False), Posture(True, False), Posture(False, True)):
        assert recipients_for(posture) == FRIENDLY_INBOXES
        assert LEAGUE_ADDRESS not in recipients_for(posture)


def test_half_armed_postures_refuse_to_run_at_all():
    for posture in (Posture(True, False), Posture(False, True)):
        with pytest.raises(ArmingError, match="half-armed"):
            assert_deliverable(posture, has_credentials=True, settled=True)
    assert_deliverable(Posture(False, False), has_credentials=False, settled=False)


def test_an_armed_run_refuses_when_it_could_not_deliver():
    armed = Posture(True, True)
    with pytest.raises(ArmingError, match="no Gmail credentials"):
        assert_deliverable(armed, has_credentials=False, settled=True)
    with pytest.raises(ArmingError, match="rule 35"):
        assert_deliverable(armed, has_credentials=True, settled=False)
    assert_deliverable(armed, has_credentials=True, settled=True)


def test_the_league_address_appears_in_exactly_one_module():
    """Structural guarantee: no other code path can name the lecturer's alias."""
    for module in (commands,):
        assert LEAGUE_ADDRESS not in inspect.getsource(module)
    source = inspect.getsource(rec)
    assert source.count(LEAGUE_ADDRESS) == 1
    assert rec.is_league_address(f" {LEAGUE_ADDRESS.upper()} ")
    assert not rec.is_league_address("someone@example.com")
