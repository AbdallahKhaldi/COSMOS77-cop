"""The four tools answer {"ok": true} instantly and enqueue; the client reopens once, honors
deadlines. All transport in-memory (fastmcp client against the server object) — no sockets."""

import asyncio

import pytest
from fastmcp import Client

from cosmos77_cop.net.client import PeerCallError, PeerClient
from cosmos77_cop.net.messages import ControlMessage, TurnMessage, now_iso
from cosmos77_cop.net.server import KIND_AUDIT, KIND_NEGOTIATE, KIND_TURN, PeerInbox, build_server


def call(server, tool, args):
    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(go())


def test_all_four_tools_return_ok_and_enqueue():
    inbox = PeerInbox()
    server = build_server(inbox, "test-peer")
    result = call(server, "negotiate", {"message": {"terms": {}}})
    assert result.data == {"ok": True}
    call(server, "receive_turn", {"message": {"step": 1, "commit": "c1"}})
    call(server, "receive_control", {"message": {"kind": "status"}})
    call(server, "submit_audit", {"payload": {"records": []}})
    kinds = [inbox.pull(0.1)[0] for _ in range(4)]
    assert kinds == [KIND_NEGOTIATE, KIND_TURN, "control", KIND_AUDIT]


def test_inbox_drops_junk_and_overflow_without_raising():
    inbox = PeerInbox(maxsize=1)
    inbox.push(KIND_TURN, "not a dict")
    inbox.push(KIND_TURN, {"step": 1})
    inbox.push(KIND_TURN, {"step": 2})
    assert inbox.dropped == 2
    assert inbox.pull(0.05) == (KIND_TURN, {"step": 1})
    assert inbox.pull(0.01) is None


def test_peer_client_calls_over_inmemory_transport_and_closes():
    inbox = PeerInbox()
    server = build_server(inbox, "test-peer")
    client = PeerClient("unused", transport_factory=lambda: Client(server))
    result = client.call("receive_turn", {"message": {"step": 1, "commit": "x"}}, deadline_s=10)
    assert getattr(result, "data", None) == {"ok": True}
    assert inbox.pull(0.1)[0] == KIND_TURN
    client.close()


def test_peer_client_reopens_once_after_transport_death():
    inbox = PeerInbox()
    server = build_server(inbox, "test-peer")
    attempts = []

    class DyingClient:
        def __init__(self):
            self.inner = Client(server)

        async def __aenter__(self):
            await self.inner.__aenter__()
            return self

        async def __aexit__(self, *exc):
            return await self.inner.__aexit__(*exc)

        async def call_tool(self, tool, args):
            attempts.append(tool)
            if len(attempts) == 1:
                raise ConnectionError("session torn")
            return await self.inner.call_tool(tool, args)

    client = PeerClient("unused", transport_factory=DyingClient)
    result = client.call("receive_control", {"message": {"kind": "status"}}, deadline_s=10)
    assert getattr(result, "data", None) == {"ok": True}
    assert len(attempts) == 2
    client.close()


def test_peer_client_deadline_expiry_raises_not_hangs():
    class HangingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def call_tool(self, tool, args):
            await asyncio.sleep(30)

    client = PeerClient("unused", transport_factory=HangingClient)
    with pytest.raises(PeerCallError, match="deadline"):
        client.call("negotiate", {"message": {}}, deadline_s=0.3)


def test_wire_messages_roundtrip_with_explicit_nulls():
    turn = TurnMessage(
        step=3, sender="thief", commit="c", hint="h", smell_grid={"1,1": 0.9}, timestamp=now_iso()
    )
    wire = turn.to_wire()
    assert wire["barrier_placed"] is None and wire["claim_response"] is None
    assert TurnMessage.from_wire(wire) == turn
    assert TurnMessage.from_wire({"step": 3, "sender": "thief", "commit": "c"}).smell_grid == {}
    control = ControlMessage(kind="quit", sender="police")
    assert ControlMessage.from_wire(control.to_wire()) == control
    assert turn.timestamp != ""


def test_the_private_connect_budget_reaches_the_tcp_handshake():
    """`connect_timeout_s` was a knob with zero reads: PeerClient only ever took `deadline_s`,
    so a cold tunnel blocked for the whole turn budget instead of failing fast."""
    import json
    from pathlib import Path

    import httpx

    from cosmos77_cop.engine.config import from_dict
    from cosmos77_cop.net.client import http_client_factory
    from cosmos77_cop.orchestrator.gateway import Gateway
    from cosmos77_cop.orchestrator.peerconf import PeerConfig

    built = http_client_factory(3.5)(headers=None, timeout=httpx.Timeout(30.0), auth=None)
    assert built.timeout.connect == 3.5
    assert built.timeout.read == 30.0 and built.timeout.write == 30.0
    assert http_client_factory(2.0)().timeout.connect == 2.0
    assert PeerClient("http://peer/mcp", connect_timeout_s=7.0).connect_timeout_s == 7.0

    # The MCP layer passes keywords of its own (`follow_redirects` today, more tomorrow). A
    # factory that rejects one of them fails EVERY dial with "Client failed to connect" —
    # which is a handshake failure in every real game, not a test-visible error.
    assert http_client_factory(1.0)(follow_redirects=True).timeout.connect == 1.0
    assert http_client_factory(1.0)(headers={"x": "y"}).headers["x"] == "y"
    defaulted = http_client_factory(1.0)()
    assert defaulted.timeout.read == 300.0 and defaulted.follow_redirects is True

    # The real dialer a real game builds carries the configured budget, not a default.
    repo = Path(__file__).resolve().parents[2]
    raw = json.loads((repo / "config" / "game.json").read_text(encoding="utf-8"))
    peer = PeerConfig(connect_timeout_s=4.0)
    gateway = Gateway(
        game_cfg=from_dict(raw), peer_cfg=peer, role="police", group_id="cosmos77",
        group_name="cosmos77", opponent_group_id="rival",
    )
    assert gateway.client.connect_timeout_s == 4.0


def test_negotiate_reply_carries_our_greeting_for_request_response_peers():
    """Kit WARNINGS 2b: a request/response opponent reads the agreement out of its own
    call's reply — a bare {"ok": true} leaves it waiting forever with healthy logs."""
    from cosmos77_cop.net.server import PeerInbox, build_server

    ours = {"terms": {"grid_size": 7}, "signature": "aa", "group_id": "cosmos77"}
    mcp = build_server(PeerInbox(), "t", greeting_provider=lambda: dict(ours))
    tool = mcp._tool_manager._tools["negotiate"]
    reply = tool.fn(message={"terms": {}, "group_id": "rival"})
    assert reply["ok"] is True
    assert reply["message"] == ours, "the reply must carry OUR greeting for them to read"


def test_negotiate_reply_stays_bare_ok_without_a_provider():
    """Standing servers (no config bound yet) keep the legacy shape — push peers ignore it."""
    from cosmos77_cop.net.server import PeerInbox, build_server

    mcp = build_server(PeerInbox(), "t")
    reply = mcp._tool_manager._tools["negotiate"].fn(message={})
    assert reply == {"ok": True}


def test_a_malformed_wire_turn_is_refused_not_crashed():
    """One garbage POST (no step/commit) from a buggy peer must never kill the series."""
    from cosmos77_cop.net.receiver import Receiver
    from cosmos77_cop.orchestrator import runtime

    class _FakeGateway:
        def __init__(self):
            self.receiver = Receiver(4)
            self.received_commits: dict[int, str] = {}

    gw = _FakeGateway()
    assert runtime.route_turn(gw, {"hint": "no step or commit here"}) == []
    assert gw.receiver.malformed == 1
    good = {"step": 1, "commit": "c" * 64}
    assert runtime.route_turn(gw, good), "a well-formed turn still applies after the refusal"


def test_handshake_accepts_a_greeting_carried_in_the_reply_body():
    """The outbound half of WARNINGS 2b: we must read the response, not only our queue."""
    from types import SimpleNamespace

    from cosmos77_cop.orchestrator import dialect

    theirs = {"terms": {"grid_size": 7}, "signature": "bb", "group_id": "rival"}

    class _Verdict:
        ok = True
        bystander = False

    captured = {}

    class _FakeGateway:
        peer_greeting = None

        @staticmethod
        def verify(candidate):
            captured["candidate"] = candidate
            return _Verdict()

    gw = _FakeGateway()
    reply = SimpleNamespace(data={"ok": True, "message": dict(theirs)})
    assert dialect.greeting_from_reply(gw, reply) is True
    assert gw.peer_greeting == theirs and captured["candidate"] == theirs
    # our own peers answer a bare ok — ignored, never refused
    assert dialect.greeting_from_reply(_FakeGateway(), SimpleNamespace(data={"ok": True})) is False
    assert dialect.greeting_from_reply(_FakeGateway(), SimpleNamespace()) is False
