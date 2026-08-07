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
