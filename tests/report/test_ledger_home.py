"""Where the ledger lives: repo file by default, the volume twin when the hub says so."""

from __future__ import annotations

from pathlib import Path

from cosmos77_cop.report.ledger import ledger_file


def test_default_is_the_committed_repo_file():
    assert ledger_file("/repo") == Path("/repo/artifacts/league_ledger.json")


def test_env_override_points_at_the_volume_twin(monkeypatch):
    """On the hub, runtime advances must not touch the working tree: the rule-53
    clean-tree gate refuses a counted run over ANY repo mutation, symlinks included."""
    monkeypatch.setenv("COSMOS_LEDGER_FILE", "/data/league_ledger.json")
    assert ledger_file("/repo") == Path("/data/league_ledger.json")
