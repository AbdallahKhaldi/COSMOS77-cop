"""Spectator pacing: a dwell after each view, off by default, never in league play."""

from __future__ import annotations

import pytest

from cosmos77_cop.orchestrator import turnloop


@pytest.fixture(autouse=True)
def _reset_pace() -> None:
    turnloop._pace_s = None


def test_pace_is_off_unless_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env: league runs play at full speed, exactly as before."""
    monkeypatch.delenv("COSMOS_TURN_DELAY_MS", raising=False)
    assert turnloop._view_pace() == 0.0


def test_pace_reads_milliseconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """A spectator run dwells the configured milliseconds after each view."""
    monkeypatch.setenv("COSMOS_TURN_DELAY_MS", "250")
    assert turnloop._view_pace() == 0.25


def test_garbage_pace_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed value can never wedge a game: it means full speed."""
    monkeypatch.setenv("COSMOS_TURN_DELAY_MS", "fast please")
    assert turnloop._view_pace() == 0.0


def test_emit_dwells_only_when_paced(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dwell rides the view hook, never the decision path."""
    slept: list[float] = []
    monkeypatch.setattr(turnloop.time, "sleep", slept.append)
    monkeypatch.setenv("COSMOS_TURN_DELAY_MS", "120")
    turnloop._emit(object(), None, None, "YOUR TURN", 1)
    assert slept == [0.12]
