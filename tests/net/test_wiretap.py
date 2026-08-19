"""The wire monitor: every call visible, faults never escape (the five-blind-windows lesson)."""

from __future__ import annotations

from cosmos77_cop.net import wiretap


def test_emit_prints_and_taps(capsys, monkeypatch):
    seen = []
    monkeypatch.setattr(wiretap, "TAP", seen.append)
    wiretap.emit("out", "receive_turn", "https://them/mcp", "ok", 34.2)
    out = capsys.readouterr().out
    assert "-> receive_turn @https://them/mcp ok 34ms" in out
    assert seen[0]["t"] == "wire" and seen[0]["direction"] == "out" and seen[0]["ms"] == 34.2


def test_inbound_arrow_and_no_tap(capsys, monkeypatch):
    monkeypatch.setattr(wiretap, "TAP", None)
    wiretap.emit("in", "negotiate", "MOAAMOHA", "recv")
    assert "<- negotiate @MOAAMOHA recv" in capsys.readouterr().out


def test_who_tag_labels_shared_streams(capsys, monkeypatch):
    # f2 runs both our roles into ONE shared events file — the tag names the speaker
    seen = []
    monkeypatch.setattr(wiretap, "TAP", seen.append)
    monkeypatch.setattr(wiretap, "WHO", "police")
    wiretap.emit("out", "receive_turn", "https://them/mcp", "ok", 5.0)
    assert " police -> receive_turn " in capsys.readouterr().out
    assert seen[0]["who"] == "police"


def test_a_broken_tap_never_raises(monkeypatch):
    def boom(event):
        raise RuntimeError("sink died")
    monkeypatch.setattr(wiretap, "TAP", boom)
    wiretap.emit("out", "x", "y", "ok", 1.0)  # must not raise


def test_client_call_taps_success_and_failure(monkeypatch):
    from types import SimpleNamespace

    from cosmos77_cop.net.client import PeerCallError, PeerClient

    events = []
    monkeypatch.setattr(wiretap, "TAP", events.append)

    class _FakeTransport:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def call_tool(self, tool, args): return SimpleNamespace(data={"ok": True})

    client = PeerClient("https://peer.example/mcp", transport_factory=_FakeTransport)
    assert client.url == "https://peer.example/mcp"
    client.call("negotiate", {"message": {}}, deadline_s=10)
    assert events and events[-1]["tool"] == "negotiate" and events[-1]["status"] == "ok"

    class _DeadTransport:
        async def __aenter__(self): raise OSError("refused")
        async def __aexit__(self, *a): return False

    dead = PeerClient("https://dead.example/mcp", transport_factory=_DeadTransport)
    try:
        dead.call("receive_turn", {"message": {}}, deadline_s=5)
    except PeerCallError:
        pass
    assert events[-1]["status"].startswith("ERR")
