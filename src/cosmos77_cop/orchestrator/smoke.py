"""The Phase-5 smoke runtime: real HTTP handshake + one committed turn each way.

Two separate processes (this repo's peer and the sibling repo's) dial each other over localhost,
exchange verified greetings, and each seals + sends exactly one turn (commit + hint + smell_grid
on the wire; nonces stay secret — there is no in-play reveal).
"""

from __future__ import annotations

import time

from ..crypto.nonce import new_nonce
from ..engine.config import load_game_config
from ..net.client import PeerCallError
from ..net.messages import TurnMessage, now_iso
from ..net.server import KIND_NEGOTIATE, KIND_TURN
from ..orchestrator import machine as sm
from ..orchestrator.gateway import Gateway
from ..orchestrator.peerconf import PeerConfig
from ..protocol.scent import smell_emit
from ..protocol.sealing import INTENT_TRUTH, VERDICT_MOVED, build_turn_payload, commit
from . import runtime


def _route_turn(gateway: Gateway, message: dict) -> None:
    for applied in gateway.receiver.ingest(message):
        gateway.received_commits[int(applied["step"])] = str(applied["commit"])


def _handshake(gateway: Gateway) -> bool:
    deadline = time.monotonic() + gateway.peer_cfg.handshake_budget_s
    sent = verified = False
    while time.monotonic() < deadline and not (sent and verified):
        if not sent:
            try:
                gateway.client.call(
                    "negotiate", {"message": gateway.greeting(new_nonce())}, deadline_s=5.0
                )
                sent = True
            except PeerCallError:
                time.sleep(0.3)
        item = gateway.inbox.pull(timeout_s=0.2)
        if item and item[0] == KIND_TURN:
            _route_turn(gateway, item[1])
        elif item and item[0] == KIND_NEGOTIATE:
            verdict = gateway.verify(item[1])
            if verdict.ok:
                verified = True
            elif not verdict.bystander:
                print(f"handshake refused: {verdict.code} {verdict.detail}")
                return False
    return sent and verified


def _send_turn(gateway: Gateway) -> None:
    cfg = gateway.game_cfg
    start = cfg.cop_start if gateway.role == "police" else cfg.thief_start
    payload = build_turn_payload(
        step=1,
        role=gateway.role,
        sub_game=gateway.sub_game_number,
        grid_size=cfg.grid_size,
        self_pos=start,
        barriers=[],
        move="MOVE:STAY",
        intent=INTENT_TRUTH,
        hint="warming up on the block",
        verdict=VERDICT_MOVED,
    )
    nonce = new_nonce()
    sealed = commit(payload, nonce)
    gateway.records.append({"payload": payload, "nonce": nonce, "commit": sealed})
    message = TurnMessage(
        step=1,
        sender=gateway.role,
        commit=sealed,
        hint=str(payload["hint"]),
        smell_grid=smell_emit(start, cfg.pheromone_center_intensity, 5, cfg.grid_size),
        timestamp=now_iso(),
    )
    gateway.client.call(
        "receive_turn", {"message": message.to_wire()}, deadline_s=gateway.peer_cfg.turn_timeout_s
    )


def _await_turn(gateway: Gateway) -> bool:
    deadline = time.monotonic() + gateway.peer_cfg.turn_timeout_s
    while time.monotonic() < deadline:
        if 1 in gateway.received_commits:
            return True
        item = gateway.inbox.pull(timeout_s=gateway.peer_cfg.poll_s)
        if item and item[0] == KIND_TURN:
            _route_turn(gateway, item[1])
    return 1 in gateway.received_commits


def run_smoke_peer(*, role: str, port: int,
    host: str = "0.0.0.0", peer_url: str, game_config_path: str) -> int:
    """Serve, dial, handshake, one committed turn each way; 0 on success."""
    gateway = Gateway(
        game_cfg=load_game_config(game_config_path),
        peer_cfg=PeerConfig(my_port=port, opponent_url=peer_url),
        role=role,
        group_id="cosmos77",
        group_name="cosmos77",
    )
    server = runtime.start_server(gateway.mcp, port, host=host)
    try:
        if not _handshake(gateway):
            return 4
        gateway.machine.transition(sm.COMPUTING_MOVE)
        if gateway.role == "thief":
            gateway.machine.transition(sm.COMMITTING)
            _send_turn(gateway)
            gateway.machine.transition(sm.AWAITING_REVEAL)
            got = _await_turn(gateway)
        else:
            got = _await_turn(gateway)
            gateway.machine.transition(sm.COMMITTING)
            _send_turn(gateway)
            gateway.machine.transition(sm.AWAITING_REVEAL)
        gateway.machine.transition(sm.VERIFYING)
        gateway.machine.transition(sm.DONE)
        print(f"smoke {gateway.role}: handshake verified, turn exchanged={got}")
        return 0 if got else 6
    finally:
        server.should_exit = True
        gateway.client.close()
