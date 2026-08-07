"""The smoke flow's handshake/turn helpers, driven with a fake client — zero sockets."""

import json
from pathlib import Path

from cosmos77_cop.engine.config import from_dict
from cosmos77_cop.net.server import KIND_NEGOTIATE, KIND_TURN
from cosmos77_cop.orchestrator.gateway import Gateway
from cosmos77_cop.orchestrator.peerconf import PeerConfig
from cosmos77_cop.orchestrator.smoke import _await_turn, _handshake, _send_turn

REPO = Path(__file__).resolve().parents[2]


class FakeClient:
    def __init__(self):
        self.calls = []

    def call(self, tool, args, *, deadline_s):
        self.calls.append((tool, args))
        return {"ok": True}

    def close(self):
        return None


def make_gateway(role="thief") -> Gateway:
    raw = json.loads((REPO / "config" / "game.json").read_text(encoding="utf-8"))
    gw = Gateway(
        game_cfg=from_dict(raw),
        peer_cfg=PeerConfig(handshake_budget_s=2.0, turn_timeout_s=1.0),
        role=role,
        group_id="cosmos77",
        group_name="cosmos77",
    )
    gw.client = FakeClient()
    return gw


def peer_greeting_for(gw: Gateway) -> dict:
    other = make_gateway(role="police" if gw.role == "thief" else "thief")
    return other.greeting(nonce="ef" * 16)


def test_handshake_succeeds_on_verified_counterpart():
    gw = make_gateway()
    gw.inbox.push(KIND_NEGOTIATE, peer_greeting_for(gw))
    assert _handshake(gw)
    assert gw.client.calls[0][0] == "negotiate"


def test_handshake_refuses_role_collision_and_keeps_waiting_then_times_out():
    gw = make_gateway()
    same_role = peer_greeting_for(gw)
    same_role["role"] = gw.role
    gw.inbox.push(KIND_NEGOTIATE, same_role)
    assert not _handshake(gw)


def test_handshake_hard_refusal_exits_immediately():
    gw = make_gateway()
    bad = peer_greeting_for(gw)
    bad["terms"] = {**bad["terms"], "setting": "Haifa"}
    bad["signature"] = "0" * 64
    gw.inbox.push(KIND_NEGOTIATE, bad)
    assert not _handshake(gw)


def test_send_turn_seals_a_record_and_ships_grid_and_commit():
    gw = make_gateway()
    _send_turn(gw)
    assert len(gw.records) == 1
    record = gw.records[0]
    tool, args = gw.client.calls[-1]
    assert tool == "receive_turn"
    wire = args["message"]
    assert wire["commit"] == record["commit"]
    assert wire["smell_grid"]["3,3"] == 0.9
    assert wire["timestamp"]
    assert "position" not in wire


def test_await_turn_applies_via_receiver_and_captures_commit():
    gw = make_gateway(role="police")
    gw.inbox.push(KIND_TURN, {"step": 1, "sender": "thief", "commit": "cc1", "hint": "x"})
    assert _await_turn(gw)
    assert gw.received_commits == {1: "cc1"}
    gw2 = make_gateway(role="police")
    assert not _await_turn(gw2)
