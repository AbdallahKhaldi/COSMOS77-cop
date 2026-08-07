"""Private per-peer runtime config: ``config/peer.toml`` overlaying documented defaults.

Never negotiated, never signed, never crosses the wire (App. B). Budgets are reconciled at load —
an impossible combination refuses to start rather than losing a game mid-flight.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ..net.receiver import reconcile_budgets


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
    hint_every_n_steps: int = 3
    hint_lie_rate: float = 0.75
    mail_burst_capacity: float = 5.0
    mail_daily_cap: int = 20
    mail_max_retries: int = 3
    mail_backoff_base_s: float = 5.0


def load_peer_config(path: str | Path | None) -> PeerConfig:
    """Load ``peer.toml`` (absent file = pure defaults) and reconcile the budgets."""
    raw: dict = {}
    if path is not None and Path(path).exists():
        raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    network = raw.get("network", {})
    trash = raw.get("trash_talk", {})
    mail = raw.get("mail", {})
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
        hint_every_n_steps=int(trash.get("every_n_steps", PeerConfig.hint_every_n_steps)),
        hint_lie_rate=float(trash.get("lie_rate", PeerConfig.hint_lie_rate)),
        mail_burst_capacity=float(mail.get("burst_capacity", PeerConfig.mail_burst_capacity)),
        mail_daily_cap=int(mail.get("daily_cap", PeerConfig.mail_daily_cap)),
        mail_max_retries=int(mail.get("max_retries", PeerConfig.mail_max_retries)),
        mail_backoff_base_s=float(mail.get("backoff_base_seconds", PeerConfig.mail_backoff_base_s)),
    )
    reconcile_budgets(
        watchdog_s=cfg.watchdog_s,
        poll_s=cfg.poll_s,
        connect_timeout_s=cfg.connect_timeout_s,
        turn_timeout_s=cfg.turn_timeout_s,
        reorder_window=cfg.reorder_window,
    )
    return cfg
