"""The six-window series driver: role alternation, fresh runtimes, settlement, artifacts.

Every window gets a completely fresh runtime (engine state, scent, tracker, nonces, handshake) —
only the transport (client, server, inbox) survives. All six windows are played even after a
failure; a series with any unsettled PLAYED window emits no result artifact and sends nothing.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..engine.config import GameConfig
from ..net.client import PeerClient
from ..net.server import KIND_NEGOTIATE, PeerInbox, build_server
from ..protocol.ids import artifact_filenames, game_id
from .brainbridge import ROLE, BrainBridge
from .gateway import Gateway
from .hintconf import hint_setup
from .peerconf import PeerConfig
from .serieslog import note_peer_repos, sealed_step0, write_window_log
from .turnloop import SubGameReport, play_sub_game
from .turnstate import SideKit, fresh_state


def window_groups(window: int, gid_a: str, gid_b: str) -> tuple[str, str]:
    """(police_gid, thief_gid) for *window*: the first-sorted group polices the odd windows."""
    first, second = sorted([gid_a, gid_b])
    return (first, second) if window % 2 == 1 else (second, first)


def _drain(inbox: PeerInbox) -> None:
    """Drop stale turn/audit traffic from the previous window — but NEVER a greeting.

    An early negotiate is the peer already at this window's handshake; eating it deadlocks us.
    """
    greetings = []
    while (item := inbox.pull(timeout_s=0.01)) is not None:
        if item[0] == KIND_NEGOTIATE:
            greetings.append(item)
    for kind, payload in greetings:
        inbox.push(kind, payload)


class SeriesDriver:
    """Runs this repo's fixed role through all windows of one series."""

    def __init__(
        self,
        *,
        game_cfg: GameConfig,
        peer_cfg: PeerConfig,
        gid_a: str,
        gid_b: str,
        out_dir: str | Path,
        code_version: str,
        num_games_declared: int | None = None,
        first_meeting: bool = True,
        hardware: dict[str, Any] | None = None,
        writer: object | None = None,
        alternate_labels: bool = True,
        scent_model: str | None = None,
        view_attachment: object | None = None,
    ) -> None:
        """One driver per process; the transport is built once and survives all windows."""
        self.cfg = game_cfg
        self.peer_cfg = peer_cfg
        self.gid_a, self.gid_b = gid_a, gid_b
        self.gid = game_id(gid_a, gid_b)
        self.out_dir = Path(out_dir)
        self.code_version = code_version
        self.num_games_declared = num_games_declared
        self.first_meeting = first_meeting
        self.hardware = hardware or {}
        self.inbox = PeerInbox(peer_cfg.queue_depth)
        self.mcp = build_server(self.inbox, f"cosmos77-series-{ROLE}")
        self.client = PeerClient(
            peer_cfg.opponent_url, connect_timeout_s=peer_cfg.connect_timeout_s
        )
        self.reports: list[SubGameReport] = []
        self.writer = writer
        self.peer_identity: dict[str, Any] | None = None
        self.alternate_labels, self.scent_model = alternate_labels, scent_model
        self.view_attachment = view_attachment
        self.hints = hint_setup(peer_cfg)  # resolved ONCE: what we run is what we declare
        self.tokens_spent = 0

    def window_roles(self, window: int) -> tuple[str, str]:
        """(police_gid, thief_gid) for *window* under this series' topology.

        Selfplay alternates the group labels (both processes are ours); against a REAL
        opponent our group id is constant and only the fixture's role changes per window.
        """
        if self.alternate_labels:
            return window_groups(window, self.gid_a, self.gid_b)
        return (self.gid_a, self.gid_b) if ROLE == "police" else (self.gid_b, self.gid_a)

    def gateway_for(self, window: int) -> Gateway:
        """A fresh per-window gateway over the surviving transport."""
        police_gid, thief_gid = self.window_roles(window)
        my_gid = police_gid if ROLE == "police" else thief_gid
        opp_gid = thief_gid if ROLE == "police" else police_gid
        return Gateway(
            game_cfg=self.cfg,
            peer_cfg=self.peer_cfg,
            role=ROLE,
            group_id=my_gid,
            group_name=my_gid,
            sub_game_number=window,
            opponent_group_id=opp_gid,
            client=self.client,
            inbox=self.inbox,
            scent_model=self.scent_model,
            counted_games_played=self.num_games_declared,
        )

    def play_window(self, window: int) -> SubGameReport:
        """Fresh runtime, one sub-game, sequenced on the previous window's log file."""
        if window > 1:
            previous = self.out_dir / artifact_filenames(self.gid, window - 1)["log"]
            deadline = time.monotonic() + self.peer_cfg.watchdog_s
            while not previous.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
        _drain(self.inbox)
        gateway = self.gateway_for(window)
        state = fresh_state(self.cfg, ROLE)
        kit = SideKit.fresh(
            self.cfg,
            ROLE,
            seed=1000 + window,
            every_n=self.peer_cfg.hint_every_n_steps,
            lie_rate=self.peer_cfg.hint_lie_rate,
            scent_model=self.scent_model,
            setup=self.hints,
            tokens_spent=self.tokens_spent,
        )
        bridge = BrainBridge(state)
        if self.view_attachment is not None:
            bridge.view_attachment = self.view_attachment
            self.view_attachment.attach(bridge, window)
        step0 = sealed_step0(self, gateway.group_id, window)
        report = play_sub_game(gateway, state, kit, bridge, step0)
        self.tokens_spent += report.tokens
        self.reports.append(report)
        if self.peer_identity is None and gateway.peer_greeting is not None:
            self.peer_identity = gateway.peer_greeting
            note_peer_repos(self, window)
        write_window_log(self, window, report)
        return report
