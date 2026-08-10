"""Private per-peer runtime config: ``config/peer.toml`` overlaying documented defaults.

Never negotiated, never signed, never crosses the wire (App. B). Budgets are reconciled at load —
an impossible combination refuses to start rather than losing a game mid-flight.

Two layers wrap the file (:mod:`.peerlayers`): the ENVIRONMENT fills keys the file omits (the hub
image has no ``peer.toml``), and the SIGNED ``config/game.json`` then overrides every parallel
key, because a term both teams agreed outranks a private preference.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..net.receiver import reconcile_budgets
from ..strategy.params import StrategyParams, from_overlay
from .identity import LLM_MODEL
from .peerlayers import GAME_CONFIG, apply_env, apply_signed


@dataclass(frozen=True)
class PeerConfig:
    """Validated per-machine runtime settings."""

    my_port: int = 8801
    opponent_url: str = "http://127.0.0.1:8802/mcp"
    turn_timeout_s: float = 30.0
    connect_timeout_s: float = 10.0
    watchdog_s: float = 60.0
    poll_s: float = 0.05
    reorder_window: int = 4
    queue_depth: int = 100
    handshake_budget_s: float = 60.0
    trash_provider: str = "template"
    trash_model: str = LLM_MODEL
    hint_timeout_s: float = 12.0
    hint_every_n_steps: int = 3
    hint_lie_rate: float = 0.75
    mail_burst_capacity: float = 5.0
    mail_daily_cap: int = 20
    mail_max_retries: int = 3
    mail_backoff_base_s: float = 5.0
    league_counted: bool = False
    #: Verbatim ``[strategy]`` overlay — ONLY the keys the operator actually set, so no
    #: strategy default is ever restated here. ``strategy/params.py`` owns the defaults;
    #: :meth:`strategy_params` is the one place that turns this into typed knobs.
    strategy: dict[str, Any] = field(default_factory=dict)

    def strategy_params(self) -> StrategyParams:
        """The documented defaults with this peer's ``[strategy]`` overlay applied."""
        return from_overlay(self.strategy)


def load_peer_config(
    path: str | Path | None, game_config_path: str | Path = GAME_CONFIG
) -> PeerConfig:
    """Load ``peer.toml`` under the env + signed layers and reconcile the budgets."""
    raw: dict = {}
    if path is not None and Path(path).exists():
        raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    raw = apply_signed(apply_env(raw), game_config_path)
    network = raw.get("network", {})
    trash = raw.get("trash_talk", {})
    mail = raw.get("mail", {})
    league = raw.get("league", {})
    cfg = PeerConfig(
        my_port=int(network.get("my_port", PeerConfig.my_port)),
        opponent_url=str(network.get("opponent_url", PeerConfig.opponent_url)),
        turn_timeout_s=float(network.get("turn_timeout_seconds", PeerConfig.turn_timeout_s)),
        connect_timeout_s=float(
            network.get("connect_timeout_seconds", PeerConfig.connect_timeout_s)
        ),
        watchdog_s=float(network.get("watchdog_seconds", PeerConfig.watchdog_s)),
        poll_s=float(network.get("poll_seconds", PeerConfig.poll_s)),
        reorder_window=int(network.get("reorder_window", PeerConfig.reorder_window)),
        queue_depth=int(network.get("queue_depth", PeerConfig.queue_depth)),
        handshake_budget_s=float(
            network.get("handshake_budget_seconds", PeerConfig.handshake_budget_s)
        ),
        trash_provider=str(trash.get("provider", PeerConfig.trash_provider)),
        trash_model=str(trash.get("model", PeerConfig.trash_model)),
        hint_timeout_s=float(trash.get("timeout_seconds", PeerConfig.hint_timeout_s)),
        hint_every_n_steps=int(trash.get("every_n_steps", PeerConfig.hint_every_n_steps)),
        hint_lie_rate=float(trash.get("lie_rate", PeerConfig.hint_lie_rate)),
        mail_burst_capacity=float(mail.get("burst_capacity", PeerConfig.mail_burst_capacity)),
        mail_daily_cap=int(mail.get("daily_cap", PeerConfig.mail_daily_cap)),
        mail_max_retries=int(mail.get("max_retries", PeerConfig.mail_max_retries)),
        mail_backoff_base_s=float(mail.get("backoff_base_seconds", PeerConfig.mail_backoff_base_s)),
        league_counted=bool(league.get("counted", PeerConfig.league_counted)),
        strategy=dict(raw.get("strategy") or {}),
    )
    reconcile_budgets(
        watchdog_s=cfg.watchdog_s,
        poll_s=cfg.poll_s,
        connect_timeout_s=cfg.connect_timeout_s,
        turn_timeout_s=cfg.turn_timeout_s,
        reorder_window=cfg.reorder_window,
    )
    cfg.strategy_params()  # a mistyped knob refuses HERE, not silently mid-series
    return cfg
