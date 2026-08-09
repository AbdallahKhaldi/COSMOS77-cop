"""Single-URL relay parity: the first-sorted gid polices the odd windows (league rule)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sparring_relay import cop_owns_odds


def test_parity_derives_from_the_sorted_gid_pair():
    assert cop_owns_odds("cosmos77", "sparring-kit") is True
    # ASCII sort: uppercase opponents sort before "cosmos77" — our cop owns the EVENS.
    assert cop_owns_odds("SMNGRP05", "cosmos77") is False
    assert cop_owns_odds("anrbj666", "cosmos77") is False
    assert cop_owns_odds("best2934", "cosmos77") is False


def test_no_gids_keeps_the_historical_default():
    assert cop_owns_odds(None, None) is True
    assert cop_owns_odds("cosmos77", None) is True
