"""The Orchestrator gateway — the single construction site for every subsystem (rule 3)."""

from __future__ import annotations

import os
from typing import Any

from ..engine.config import GameConfig
from ..net.client import PeerClient
from ..net.handshake import Verdict, build_greeting, verify_peer
from ..net.receiver import Receiver
from ..net.server import PeerInbox, build_server
from ..orchestrator.machine import StateMachine
from ..orchestrator.peerconf import PeerConfig
from ..protocol.ids import game_uid
from ..protocol.locks import OUR_LOCKS, REGISTERED
from ..protocol.terms import terms_from_config
from . import identity
from .deadline import DeadlineClock


class Gateway:
    """Wires inbox, server, client, receiver, machine and identity for one sub-game."""

    def __init__(
        self,
        *,
        game_cfg: GameConfig,
        peer_cfg: PeerConfig,
        role: str,
        group_id: str,
        group_name: str,
        sub_game_number: int = 1,
        opponent_group_id: str | None = None,
        client: PeerClient | None = None,
        inbox: PeerInbox | None = None,
        scent_model: str | None = None,
        counted_games_played: int | None = None,
    ) -> None:
        """Build every subsystem from validated config — nothing else constructs them.

        *counted_games_played* is the rule-37 truthful declaration (exclusive of this game);
        when given it rides the greeting identity block.
        """
        self.game_cfg = game_cfg
        self.peer_cfg = peer_cfg
        self.role = role
        self.group_id = group_id
        self.sub_game_number = sub_game_number
        self.opponent_group_id = opponent_group_id
        self.terms = terms_from_config(game_cfg.raw)
        self.uid = (
            game_uid(self.terms, group_id, opponent_group_id) if opponent_group_id else None
        )
        public_url = os.environ.get("COSMOS_PUBLIC_MCP_URL")
        self.identity: dict[str, Any] = {
            "group_id": group_id,
            "group_name": group_name,
            "llm_model": identity.LLM_MODEL,
            "mcp_servers": {"self": public_url or f"http://127.0.0.1:{peer_cfg.my_port}/mcp"},
            "repos": dict(identity.TEAM_REPOS),
            "members": list(identity.MEMBER_IDS),
        }
        if counted_games_played is not None:
            self.identity["counted_games_played"] = int(counted_games_played)
        self.inbox = inbox or PeerInbox(peer_cfg.queue_depth)
        self.mcp = build_server(self.inbox, f"cosmos77-{role}")
        self.client = client or PeerClient(peer_cfg.opponent_url)
        self.receiver = Receiver(peer_cfg.reorder_window)
        self.machine = StateMachine()
        self.clock = DeadlineClock(0.0)
        self.records: list[dict[str, Any]] = []
        self.received_commits: dict[int, str] = {}
        self.pending_turns: list[dict[str, Any]] = []
        self.pending_audits: list[dict[str, Any]] = []
        self.pending_greetings: list[dict[str, Any]] = []
        self.locks = dict(OUR_LOCKS)
        if scent_model is not None:
            self.locks["scent_model"] = REGISTERED[("scent_model", scent_model)]
        self.peer_greeting: dict[str, Any] | None = None

    def greeting(self, nonce: str) -> dict[str, Any]:
        """Our negotiate message for this sub-game."""
        return build_greeting(
            terms=self.terms,
            nonce=nonce,
            group_id=self.group_id,
            role=self.role,
            sub_game_number=self.sub_game_number,
            identity=self.identity,
            locks=dict(self.locks),
            game_uid=self.uid,
        )

    def verify(self, theirs: object) -> Verdict:
        """Validate an inbound greeting against ours, pinned to the configured opponent."""
        return verify_peer(
            ours=self.greeting(nonce="0" * 32),
            theirs=theirs,
            our_uid=self.uid,
            expected_gid=self.opponent_group_id,
        )
