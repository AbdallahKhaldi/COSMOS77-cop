"""Window choreography barrier — the f2-20260819-203304 five-zeroed-windows lesson."""

from __future__ import annotations

import threading

from cosmos77_cop.orchestrator.sequence import (
    await_predecessors,
    gate,
    sealed_windows,
    todo_windows,
)


def _seal(tmp_path, w: int) -> None:
    (tmp_path / f"log_A-vs-B_g{w:02d}.json").write_text("{}", encoding="utf-8")


def test_todo_windows_split_and_full():
    assert todo_windows("2,4,6", 6) == [2, 4, 6]
    assert todo_windows(None, 3) == [1, 2, 3]


def test_sealed_windows_reads_only_window_logs(tmp_path):
    _seal(tmp_path, 1)
    _seal(tmp_path, 3)
    (tmp_path / "log_A-vs-B_gXX.json").write_text("{}", encoding="utf-8")  # not a seal
    (tmp_path / "result_A-vs-B.json").write_text("{}", encoding="utf-8")
    assert sealed_windows(tmp_path) == {1, 3}


def test_await_predecessors_returns_when_artifacts_land(tmp_path):
    _seal(tmp_path, 1)
    timer = threading.Timer(0.15, _seal, args=(tmp_path, 2))
    timer.start()
    try:
        assert await_predecessors(tmp_path, 3, timeout_s=5.0, poll_s=0.02)
    finally:
        timer.cancel()


def test_await_predecessors_times_out(tmp_path):
    assert not await_predecessors(tmp_path, 2, timeout_s=0.05, poll_s=0.01)


def test_gate_passes_selfplay_and_window_one_through(tmp_path):
    gate(tmp_path, 5, armed=False, timeout_s=0.01)  # selfplay: no barrier, no wait
    gate(tmp_path, 1, armed=True, timeout_s=0.01)  # first window never waits


def test_gate_prints_and_degrades_on_timeout(tmp_path, capsys):
    gate(tmp_path, 2, armed=True, timeout_s=0.05)
    out = capsys.readouterr().out
    assert "g02 barrier" in out and "playing anyway" in out
